"""FastAPI routes for the FreeFlow AI Management API (/api).

Provides authenticated endpoints for inspecting providers, testing connectivity,
browsing/refreshing the model catalog, querying routing profiles, and viewing
sanitized gateway diagnostics.
"""

import re
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from backend.api.deps import (
    get_catalog,
    get_provider_registry,
    get_routing_engine,
    verify_token,
)
from backend.catalog.service import ModelCatalog
from backend.logger import logger
from backend.providers.registry import ProviderRegistry
from backend.routing.engine import RoutingEngine

from .models import (
    CatalogListResponse,
    CatalogModelItem,
    CatalogRefreshRequestPayload,
    CatalogRefreshResponse,
    DatabaseDiagnostics,
    GatewayDiagnosticsResponse,
    ModelCapabilitySchema,
    ProfileListResponse,
    ProviderItem,
    ProviderListResponse,
    ProviderRefreshSummary,
    ProviderTestResponse,
    RoutingProfileItem,
)

management_router = APIRouter(prefix="/api", tags=["Management"])


def sanitize_error(message: str | None) -> str | None:
    """Sanitize error messages to eliminate secrets, tokens, and raw filesystem paths."""
    if not message:
        return None
    # Strip bearer tokens, api keys, authorization headers
    sanitized = re.sub(
        r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1[REDACTED]", message, flags=re.IGNORECASE
    )
    sanitized = re.sub(
        r"(key[=:]\s*)[A-Za-z0-9_\-\.]+", r"\1[REDACTED]", sanitized, flags=re.IGNORECASE
    )
    sanitized = re.sub(
        r"(token[=:]\s*)[A-Za-z0-9_\-\.]+", r"\1[REDACTED]", sanitized, flags=re.IGNORECASE
    )
    # Strip windows/unix paths
    sanitized = re.sub(r"[A-Za-z]:\\[\w\\\.\-]+", "[PATH]", sanitized)
    sanitized = re.sub(r"/(?:[\w\.\-]+/)+[\w\.\-]+", "[PATH]", sanitized)
    # Truncate overly long error traces
    if len(sanitized) > 300:
        sanitized = sanitized[:300] + "..."
    return sanitized


@management_router.get(
    "/providers",
    response_model=ProviderListResponse,
    summary="List registered provider adapters and non-secret configuration",
)
async def list_providers(
    request: Request,
    _token: str = Depends(verify_token),  # noqa: B008
    catalog: ModelCatalog = Depends(get_catalog),  # noqa: B008
    registry: ProviderRegistry = Depends(get_provider_registry),  # noqa: B008
) -> ProviderListResponse:
    """Return all registered provider adapters and their non-secret configuration.

    Derives data from the active ProviderRegistry and persisted non-secret configuration.
    Never exposes API keys, bearer tokens, or raw credential strings.
    """
    catalog_repo = getattr(request.app.state, "catalog_repo", None)
    saved_providers: dict[str, dict[str, Any]] = {}
    if catalog_repo is not None:
        try:
            persisted = catalog_repo.load_all_providers()
            saved_providers = {p["id"]: p for p in persisted}
        except Exception as exc:
            logger.warning("Failed to load provider configs for listing", error=str(exc))

    items: list[ProviderItem] = []
    for adapter_id in registry.list_adapters():
        adapter = registry.get(adapter_id)
        if adapter is None:
            continue

        ctx = catalog.get_provider_context(adapter_id)
        persisted_info = saved_providers.get(adapter_id, {})

        display_name = persisted_info.get("display_name") or adapter_id.capitalize()
        enabled = persisted_info.get("enabled", True)
        base_url = ctx.base_url or getattr(adapter, "_default_base_url", None)
        has_credential = bool(ctx.api_key)
        is_local = (adapter_id == "ollama") or getattr(adapter, "is_local", False)

        items.append(
            ProviderItem(
                id=adapter_id,
                display_name=display_name,
                enabled=enabled,
                base_url=base_url,
                has_credential=has_credential,
                local=is_local,
            )
        )

    # Sort predictably by provider id
    items.sort(key=lambda p: p.id)
    return ProviderListResponse(data=items)


@management_router.post(
    "/providers/{provider_id}/test",
    response_model=ProviderTestResponse,
    summary="Test connectivity to a specific provider",
)
async def test_provider_connection(
    provider_id: str,
    _token: str = Depends(verify_token),  # noqa: B008
    catalog: ModelCatalog = Depends(get_catalog),  # noqa: B008
    registry: ProviderRegistry = Depends(get_provider_registry),  # noqa: B008
) -> ProviderTestResponse:
    """Safely test provider connectivity via its adapter interface."""
    adapter = registry.get(provider_id)
    if adapter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider {provider_id!r} is not registered",
        )

    ctx = catalog.get_provider_context(provider_id)
    try:
        health = await adapter.test_connection(ctx)
        status_str = "healthy" if health.healthy else "unhealthy"
        return ProviderTestResponse(
            provider_id=provider_id,
            status=status_str,
            latency_ms=health.latency_ms,
            error=sanitize_error(health.message) if not health.healthy else None,
        )
    except Exception as exc:
        logger.warning(
            "Provider connectivity test raised unexpected exception",
            provider_id=provider_id,
            error=str(exc),
        )
        return ProviderTestResponse(
            provider_id=provider_id,
            status="error",
            latency_ms=None,
            error=sanitize_error(str(exc)),
        )


@management_router.get(
    "/catalog",
    response_model=CatalogListResponse,
    summary="Browse models in the model catalog",
)
async def get_catalog_models(
    provider_id: str | None = None,
    _token: str = Depends(verify_token),  # noqa: B008
    catalog: ModelCatalog = Depends(get_catalog),  # noqa: B008
) -> CatalogListResponse:
    """Return all catalog entries including active and stale models for dashboard inspection."""
    entries = catalog.list_entries(provider_id=provider_id, include_stale=True)
    items: list[CatalogModelItem] = []

    for entry in entries:
        items.append(
            CatalogModelItem(
                composite_id=entry.composite_id,
                provider_id=entry.provider_id,
                model_id=entry.model_id,
                display_name=entry.display_name,
                is_local=entry.is_local,
                capabilities=ModelCapabilitySchema(
                    supports_streaming=entry.capabilities.supports_streaming,
                    supports_tools=entry.capabilities.supports_tools,
                    supports_vision=entry.capabilities.supports_vision,
                    context_window=entry.capabilities.context_window,
                ),
                is_stale=entry.is_stale,
                last_seen_at=entry.last_seen_at,
                last_checked_at=entry.last_checked_at,
            )
        )

    # list_entries already sorts by (provider_id, model_id)
    return CatalogListResponse(data=items)


@management_router.post(
    "/catalog/refresh",
    response_model=CatalogRefreshResponse,
    summary="Trigger on-demand discovery refresh for all or single provider",
)
async def refresh_catalog(
    payload: CatalogRefreshRequestPayload = Body(default_factory=CatalogRefreshRequestPayload),  # noqa: B008
    _token: str = Depends(verify_token),  # noqa: B008
    catalog: ModelCatalog = Depends(get_catalog),  # noqa: B008
    registry: ProviderRegistry = Depends(get_provider_registry),  # noqa: B008
) -> CatalogRefreshResponse:
    """Trigger model catalog discovery across providers using existing locks and persistence."""
    summaries: list[ProviderRefreshSummary] = []

    if payload.provider_id:
        if registry.get(payload.provider_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {payload.provider_id!r} is not registered",
            )
        result = await catalog.refresh_provider(payload.provider_id)
        summaries.append(
            ProviderRefreshSummary(
                provider_id=result.provider_id,
                success=result.success,
                models_count=result.models_count,
                error=sanitize_error(result.error),
                timestamp=result.timestamp,
            )
        )
    else:
        results = await catalog.refresh_all()
        for r in results:
            summaries.append(
                ProviderRefreshSummary(
                    provider_id=r.provider_id,
                    success=r.success,
                    models_count=r.models_count,
                    error=sanitize_error(r.error),
                    timestamp=r.timestamp,
                )
            )

    successful = sum(1 for s in summaries if s.success)
    failed = len(summaries) - successful

    return CatalogRefreshResponse(
        total_refreshed=len(summaries),
        successful_refreshes=successful,
        failed_refreshes=failed,
        results=summaries,
    )


@management_router.get(
    "/profiles",
    response_model=ProfileListResponse,
    summary="List all active routing profiles and their configurations",
)
async def list_profiles(
    _token: str = Depends(verify_token),  # noqa: B008
    engine: RoutingEngine = Depends(get_routing_engine),  # noqa: B008
) -> ProfileListResponse:
    """Return all routing profiles registered with the RoutingEngine (built-in and custom)."""
    items: list[RoutingProfileItem] = []
    for profile in engine.get_all_profiles():
        items.append(
            RoutingProfileItem(
                name=profile.name,
                description=profile.description,
                candidates=profile.candidates,
                max_retries=profile.max_retries,
                timeout_seconds=profile.timeout_seconds,
                required_capabilities=ModelCapabilitySchema(
                    supports_streaming=profile.required_capabilities.supports_streaming,
                    supports_tools=profile.required_capabilities.supports_tools,
                    supports_vision=profile.required_capabilities.supports_vision,
                    context_window=profile.required_capabilities.context_window,
                ),
            )
        )

    items.sort(key=lambda p: p.name)
    return ProfileListResponse(data=items)


@management_router.get(
    "/diagnostics",
    response_model=GatewayDiagnosticsResponse,
    summary="Sanitized gateway diagnostics and persistence subsystem health",
)
async def get_diagnostics(
    request: Request,
    _token: str = Depends(verify_token),  # noqa: B008
    catalog: ModelCatalog = Depends(get_catalog),  # noqa: B008
    engine: RoutingEngine = Depends(get_routing_engine),  # noqa: B008
    registry: ProviderRegistry = Depends(get_provider_registry),  # noqa: B008
) -> GatewayDiagnosticsResponse:
    """Provide a safe diagnostic summary for local gateway monitoring."""
    db_mgr = getattr(request.app.state, "db_manager", None)
    if db_mgr is not None:
        db_health = db_mgr.get_health_status()
        journal_mode = None
        if db_mgr.is_initialized and not db_mgr.is_degraded:
            journal_mode = "wal" if db_mgr.db_path != ":memory:" else "memory"

        db_diag = DatabaseDiagnostics(
            available=bool(db_health.get("available", False)),
            degraded=bool(db_health.get("degraded", False)),
            mode=str(db_health.get("mode", "none")),
            reason=sanitize_error(db_health.get("reason")),
            journal_mode=journal_mode,
        )
    else:
        db_diag = DatabaseDiagnostics(
            available=False,
            degraded=True,
            mode="none",
            reason="DatabaseManager not initialized",
            journal_mode=None,
        )

    all_entries = catalog.list_entries(include_stale=True)
    stale_count = sum(1 for e in all_entries if e.is_stale)

    return GatewayDiagnosticsResponse(
        status="ok",
        database=db_diag,
        registered_providers_count=len(registry.list_adapters()),
        catalog_entries_count=len(all_entries),
        stale_models_count=stale_count,
        routing_profiles_count=len(engine.list_profiles()),
    )
