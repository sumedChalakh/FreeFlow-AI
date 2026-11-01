"""Target and candidate resolution for FreeFlow AI Routing Engine.

Provides colon-safe model resolution, separating provider ID from model ID
only when the prefix matches a registered provider. Preserves full raw model IDs,
including internal colons (e.g. 'ollama:llama3.2:3b').
"""

from backend.catalog.models import CatalogEntry
from backend.catalog.service import ModelCatalog, default_catalog
from backend.providers.base import ChatCompletionRequest
from backend.providers.errors import ModelNotFoundError, UnsupportedCapabilityError
from backend.providers.registry import ProviderRegistry
from backend.providers.registry import registry as default_registry

from .models import RoutingProfile, TargetResolution


class ModelResolver:
    """Resolves requested targets or profiles into eligible candidate deployments."""

    def __init__(
        self,
        catalog: ModelCatalog | None = None,
        registry: ProviderRegistry | None = None,
    ) -> None:
        self._catalog = catalog or default_catalog
        self._registry = registry or default_registry

    def parse_target(self, target: str) -> TargetResolution:
        """Parse a requested target string into provider and model components.

        Colon-safe rule:
        Only treats the prefix as a provider_id if it exactly matches a registered
        provider in ProviderRegistry. Otherwise, the entire string is treated as a
        model_id (e.g. 'llama3.2:3b' is an Ollama model tag, not a provider named 'llama3.2').
        """
        target = target.strip()

        if ":" in target:
            prefix, sep, remainder = target.partition(":")
            if self._registry.get(prefix) is not None:
                # Registered provider prefix -> explicit deployment
                return TargetResolution(
                    provider_id=prefix,
                    model_id=remainder,
                    composite_id=f"{prefix}:{remainder}",
                    is_explicit=True,
                )

        # Unprefixed or prefix is not a known registered provider
        return TargetResolution(
            provider_id="",
            model_id=target,
            composite_id="",
            is_explicit=False,
        )

    def resolve_candidates(
        self,
        request: ChatCompletionRequest,
        *,
        target: str | None = None,
        profile: RoutingProfile | None = None,
        include_stale: bool = False,
    ) -> list[CatalogEntry]:
        """Resolve a request into an ordered list of eligible CatalogEntry deployments.

        - If target is explicit (e.g. 'ollama:llama3.2:3b'): returns exactly that deployment.
        - If target is a model name: finds matching deployments across providers.
        - If profile is provided: resolves configured candidates in priority order.
        - Validates required capabilities (e.g. streaming, tools, vision).
        """
        if target:
            resolution = self.parse_target(target)

            if resolution.is_explicit:
                entry = self._catalog.get_by_composite_id(resolution.composite_id)
                if entry is None:
                    raise ModelNotFoundError(
                        resolution.model_id,
                        provider_id=resolution.provider_id,
                    )

                # Verify capability constraints for explicit deployment
                if request.stream and not entry.capabilities.supports_streaming:
                    raise UnsupportedCapabilityError(
                        f"Model {resolution.composite_id!r} does not support streaming",
                        provider_id=resolution.provider_id,
                    )

                return [entry]

            # Model ID without registered provider prefix
            deployments = self._catalog.find_deployments(
                resolution.model_id,
                include_stale=include_stale,
            )
            if not deployments and not include_stale:
                deployments = self._catalog.find_deployments(
                    resolution.model_id,
                    include_stale=True,
                )

            if not deployments:
                raise ModelNotFoundError(
                    resolution.model_id,
                    provider_id="catalog",
                )

            # Filter candidates by capabilities required by the request
            valid_candidates = []
            for dep in deployments:
                if request.stream and not dep.capabilities.supports_streaming:
                    continue
                valid_candidates.append(dep)

            if not valid_candidates:
                raise UnsupportedCapabilityError(
                    f"No deployment of {resolution.model_id!r} supports requested capabilities",
                    provider_id="catalog",
                )

            return valid_candidates

        if profile:
            candidates: list[CatalogEntry] = []
            seen_composite_ids: set[str] = set()

            for item in profile.candidates:
                res = self.parse_target(item)
                item_deployments: list[CatalogEntry] = []

                if res.is_explicit:
                    entry = self._catalog.get_by_composite_id(res.composite_id)
                    if entry is not None and (include_stale or not entry.is_stale):
                        item_deployments.append(entry)
                else:
                    item_deployments = self._catalog.find_deployments(
                        res.model_id,
                        include_stale=include_stale,
                    )

                for dep in item_deployments:
                    if dep.composite_id in seen_composite_ids:
                        continue

                    # Filter by profile baseline requirements
                    if (
                        profile.required_capabilities.supports_streaming
                        and not dep.capabilities.supports_streaming
                    ):
                        continue
                    if (
                        profile.required_capabilities.supports_vision
                        and not dep.capabilities.supports_vision
                    ):
                        continue
                    if (
                        profile.required_capabilities.supports_tools
                        and not dep.capabilities.supports_tools
                    ):
                        continue

                    # Filter by request-level requirements
                    if request.stream and not dep.capabilities.supports_streaming:
                        continue

                    seen_composite_ids.add(dep.composite_id)
                    candidates.append(dep)

            if not candidates:
                raise ModelNotFoundError(
                    f"No eligible deployments found for profile {profile.name!r}",
                    provider_id="routing",
                )

            return candidates

        raise ModelNotFoundError(
            "Neither target nor profile was specified for routing",
            provider_id="routing",
        )
