"""Unified Model Catalog service for FreeFlow AI.

Discovers, aggregates, caches, and queries model inventory across registered
providers with fault isolation, stale tracking, and unambiguous composite IDs.
"""

import asyncio
import time
from typing import Any

from backend.logger import logger
from backend.providers.base import ProviderContext
from backend.providers.registry import ProviderRegistry
from backend.providers.registry import registry as default_registry

from .models import CatalogEntry, CatalogRefreshResult


class ModelCatalog:
    """Manages the catalog of models available across all registered AI providers."""

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        repository: Any = None,
    ) -> None:
        self._registry = registry or default_registry
        self._repository = repository
        self._contexts: dict[str, ProviderContext] = {}
        # Stores entries keyed by composite_id ("<provider_id>:<model_id>")
        self._entries: dict[str, CatalogEntry] = {}
        self._provider_locks: dict[str, asyncio.Lock] = {}

    def set_repository(self, repository: Any) -> None:
        """Set or update the backing catalog repository."""
        self._repository = repository

    async def restore_from_repository(self) -> int:
        """Restore persisted catalog entries from the repository into memory.

        Safeguard: Entries are restored as stale until active discovery confirms them.
        """
        if self._repository is None:
            return 0

        entries = await self._repository.db.run_in_thread(self._repository.load_all_entries)
        for entry in entries:
            self._entries[entry.composite_id] = entry
        return len(entries)

    def _get_provider_lock(self, provider_id: str) -> asyncio.Lock:
        """Get or create an asyncio lock for serializing discovery per provider."""
        if provider_id not in self._provider_locks:
            self._provider_locks[provider_id] = asyncio.Lock()
        return self._provider_locks[provider_id]

    def set_provider_context(self, provider_id: str, context: ProviderContext) -> None:
        """Configure runtime context (credentials, base URL, timeout) for a provider."""
        self._contexts[provider_id] = context

    def get_provider_context(self, provider_id: str) -> ProviderContext:
        """Retrieve configured context for a provider, or default if unset."""
        return self._contexts.get(provider_id, ProviderContext())

    def clear(self) -> None:
        """Clear all entries, provider contexts, and locks from the catalog."""
        self._entries.clear()
        self._contexts.clear()
        self._provider_locks.clear()

    async def refresh_provider(
        self,
        provider_id: str,
        context: ProviderContext | None = None,
    ) -> CatalogRefreshResult:
        """Discover models from a single provider and update catalog state.

        On failure, prior entries for this provider are retained but marked stale.
        One provider failure never impacts other providers in the catalog.
        """
        adapter = self._registry.get(provider_id)
        if adapter is None:
            err_msg = f"Provider {provider_id!r} is not registered"
            logger.warning("Catalog refresh failed: unregistered provider", provider_id=provider_id)
            return CatalogRefreshResult(
                provider_id=provider_id,
                success=False,
                models_count=0,
                error=err_msg,
            )

        ctx = context or self.get_provider_context(provider_id)
        lock = self._get_provider_lock(provider_id)

        async with lock:
            now = time.time()
            try:
                discovered_models = await adapter.list_models(ctx)

                # Deduplicate by model ID within this provider's output
                seen_ids: set[str] = set()
                unique_models = []
                for m in discovered_models:
                    if m.id not in seen_ids:
                        seen_ids.add(m.id)
                        unique_models.append(m)

                # Existing entries for this provider
                current_provider_entries = [
                    entry
                    for entry in list(self._entries.values())
                    if entry.provider_id == provider_id
                ]

                omitted_ids = {
                    old_entry.model_id
                    for old_entry in current_provider_entries
                    if old_entry.model_id not in seen_ids
                }

                # Safeguard 4: Commit persistent changes before publishing in-memory state
                if self._repository is not None:
                    await self._repository.db.run_in_thread(
                        self._repository.save_provider_refresh,
                        provider_id,
                        unique_models,
                        omitted_ids,
                        now,
                    )

                # Update in-memory state after persistence succeeds
                for old_entry in current_provider_entries:
                    if old_entry.model_id in omitted_ids:
                        old_entry.is_stale = True
                        old_entry.last_checked_at = now

                # Insert or update discovered models in memory
                for model in unique_models:
                    composite_id = f"{provider_id}:{model.id}"
                    existing = self._entries.get(composite_id)

                    if existing is not None:
                        # Update metadata and refresh freshness
                        existing.display_name = model.display_name
                        existing.capabilities = model.capabilities
                        existing.is_local = model.is_local
                        existing.is_stale = False
                        existing.last_seen_at = now
                        existing.last_checked_at = now
                    else:
                        self._entries[composite_id] = CatalogEntry.from_provider_model(
                            model,
                            checked_at=now,
                            seen_at=now,
                            is_stale=False,
                        )

                logger.info(
                    "Catalog refreshed provider",
                    provider_id=provider_id,
                    models_count=len(unique_models),
                )
                return CatalogRefreshResult(
                    provider_id=provider_id,
                    success=True,
                    models_count=len(unique_models),
                    timestamp=now,
                )

            except Exception as exc:
                # Fault isolation: keep prior entries, mark them stale
                logger.warning(
                    "Catalog provider discovery failed; preserving stale entries",
                    provider_id=provider_id,
                    error=str(exc),
                )
                if self._repository is not None:
                    try:
                        await self._repository.db.run_in_thread(
                            self._repository.mark_provider_stale,
                            provider_id,
                            now,
                        )
                    except Exception as repo_exc:
                        logger.warning(
                            "Failed to update stale status in repository",
                            error=str(repo_exc),
                        )

                for entry in list(self._entries.values()):
                    if entry.provider_id == provider_id:
                        entry.is_stale = True
                        entry.last_checked_at = now

                return CatalogRefreshResult(
                    provider_id=provider_id,
                    success=False,
                    models_count=sum(
                        1 for e in list(self._entries.values()) if e.provider_id == provider_id
                    ),
                    error=str(exc),
                    timestamp=now,
                )

    async def refresh_all(
        self,
        contexts: dict[str, ProviderContext] | None = None,
    ) -> list[CatalogRefreshResult]:
        """Refresh models across all registered providers with fault isolation."""
        contexts = contexts or {}
        results: list[CatalogRefreshResult] = []

        for provider_id in self._registry.list_adapters():
            ctx = contexts.get(provider_id)
            res = await self.refresh_provider(provider_id, context=ctx)
            results.append(res)

        return results

    def get_entry(self, provider_id: str, model_id: str) -> CatalogEntry | None:
        """Lookup a catalog entry by provider ID and model ID."""
        return self._entries.get(f"{provider_id}:{model_id}")

    def get_by_composite_id(self, composite_id: str) -> CatalogEntry | None:
        """Lookup a catalog entry by composite ID ('<provider_id>:<model_id>')."""
        return self._entries.get(composite_id)

    def find_deployments(
        self,
        model_id: str,
        *,
        include_stale: bool = False,
    ) -> list[CatalogEntry]:
        """Find all provider deployments matching a given model identifier."""
        matches = []
        for entry in list(self._entries.values()):
            if entry.model_id == model_id:
                if not include_stale and entry.is_stale:
                    continue
                matches.append(entry)
        return matches

    def list_entries(
        self,
        *,
        provider_id: str | None = None,
        is_local: bool | None = None,
        include_stale: bool = True,
        supports_vision: bool | None = None,
        supports_tools: bool | None = None,
        supports_streaming: bool | None = None,
    ) -> list[CatalogEntry]:
        """List and filter catalog entries."""
        results: list[CatalogEntry] = []

        for entry in list(self._entries.values()):
            if provider_id is not None and entry.provider_id != provider_id:
                continue
            if is_local is not None and entry.is_local != is_local:
                continue
            if not include_stale and entry.is_stale:
                continue
            if (
                supports_vision is not None
                and entry.capabilities.supports_vision != supports_vision
            ):
                continue
            if supports_tools is not None and entry.capabilities.supports_tools != supports_tools:
                continue
            if (
                supports_streaming is not None
                and entry.capabilities.supports_streaming != supports_streaming
            ):
                continue

            results.append(entry)

        # Sort predictably by provider_id, then model_id
        return sorted(results, key=lambda e: (e.provider_id, e.model_id))


# Module-level default catalog instance
default_catalog = ModelCatalog()
