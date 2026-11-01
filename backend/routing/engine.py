"""Intelligent Routing Engine with Bounded Automatic Failover for FreeFlow AI.

Orchestrates candidate selection, explicit target resolution, health/cooldown tracking,
capability verification, and safe failover on retryable provider errors.
Produces structured telemetry decision events without logging prompt or message contents.
"""

import time
from collections.abc import Callable

from backend.catalog.models import CatalogEntry
from backend.catalog.service import ModelCatalog, default_catalog
from backend.logger import logger
from backend.providers.base import (
    ChatCompletionRequest,
    ChatCompletionResponse,
)
from backend.providers.errors import (
    ErrorCategory,
    ModelNotFoundError,
    ProviderError,
    ProviderUnavailableError,
)
from backend.providers.registry import ProviderRegistry
from backend.providers.registry import registry as default_registry

from .cooldown import CooldownTracker
from .models import (
    FailoverAttempt,
    RoutingDecisionEvent,
    RoutingProfile,
    TargetResolution,
)
from .resolver import ModelResolver


class RoutingExhaustedError(ProviderUnavailableError):
    """Raised when all candidate deployments in a profile fail or are in cooldown."""

    def __init__(
        self,
        message: str = "All candidate deployments failed or are in cooldown",
        *,
        provider_id: str = "routing",
        status_code: int = 503,
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message,
            provider_id=provider_id,
            status_code=status_code,
            details=details,
        )


class RoutingEngine:
    """Core routing engine orchestrating provider execution, failover, and telemetry."""

    def __init__(
        self,
        catalog: ModelCatalog | None = None,
        registry: ProviderRegistry | None = None,
        cooldown_tracker: CooldownTracker | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._catalog = catalog or default_catalog
        self._registry = registry or default_registry
        self._clock = clock
        self._cooldown = cooldown_tracker or CooldownTracker(clock=clock)
        self._resolver = ModelResolver(catalog=self._catalog, registry=self._registry)
        self._profiles: dict[str, RoutingProfile] = {}
        self._init_default_profiles()

    def _init_default_profiles(self) -> None:
        """Register default routing profiles."""
        self._profiles["default"] = RoutingProfile(
            name="default",
            description="Default text chat profile",
            candidates=[],
            max_retries=2,
        )
        self._profiles["coding"] = RoutingProfile(
            name="coding",
            description="Coding and code completion profile",
            candidates=[],
            max_retries=2,
        )
        self._profiles["fast"] = RoutingProfile(
            name="fast",
            description="Low-latency and local-first inference profile",
            candidates=[],
            max_retries=2,
        )
        self._profiles["reasoning"] = RoutingProfile(
            name="reasoning",
            description="Complex reasoning profile",
            candidates=[],
            max_retries=2,
        )

    def register_profile(self, profile: RoutingProfile) -> None:
        """Register or update a routing profile."""
        self._profiles[profile.name] = profile
        logger.info("Registered routing profile", profile_name=profile.name)

    def get_profile(self, name: str) -> RoutingProfile | None:
        """Retrieve a registered routing profile by name."""
        return self._profiles.get(name)

    def list_profiles(self) -> list[str]:
        """Return the names of all registered routing profiles."""
        return sorted(self._profiles.keys())

    def get_all_profiles(self) -> list[RoutingProfile]:
        """Return all registered routing profiles."""
        return list(self._profiles.values())

    @property
    def cooldown_tracker(self) -> CooldownTracker:
        """Access the health and cooldown tracker."""
        return self._cooldown

    @property
    def resolver(self) -> ModelResolver:
        """Access the target resolver."""
        return self._resolver

    def _select_profile_candidates(
        self,
        profile: RoutingProfile,
        request: ChatCompletionRequest,
    ) -> list[CatalogEntry]:
        """Resolve candidates for a profile.

        If profile has an explicit candidates list, resolves that priority list.
        If profile has empty candidates, automatically discovers from catalog.
        """
        if profile.candidates:
            return self._resolver.resolve_candidates(request, profile=profile)

        # Dynamic catalog discovery when profile candidate list is empty
        all_entries = self._catalog.list_entries(include_stale=False)

        # Apply profile-specific filters
        if profile.name == "fast":
            # Prioritize local models
            candidates = [e for e in all_entries if e.is_local]
            if not candidates:
                candidates = all_entries
        elif profile.name == "coding":
            candidates = [
                e
                for e in all_entries
                if any(kw in e.model_id.lower() for kw in ("code", "coder", "qwen"))
            ]
            if not candidates:
                candidates = all_entries
        elif profile.name == "reasoning":
            candidates = [
                e
                for e in all_entries
                if any(kw in e.model_id.lower() for kw in ("r1", "reasoning", "deepseek"))
            ]
            if not candidates:
                candidates = all_entries
        else:
            candidates = all_entries

        # Filter by streaming requirement if requested
        if request.stream:
            candidates = [e for e in candidates if e.capabilities.supports_streaming]

        if not candidates:
            raise ModelNotFoundError(
                f"No available catalog deployments match profile {profile.name!r}",
                provider_id="routing",
            )

        return candidates

    async def complete_chat(
        self,
        request: ChatCompletionRequest,
        *,
        target: str | None = None,
        profile_name: str | None = None,
        request_id: str | None = None,
    ) -> tuple[ChatCompletionResponse, RoutingDecisionEvent]:
        """Execute a chat completion request with intelligent routing and bounded failover.

        Args:
            request: The normalized chat request.
            target: Optional target model string (e.g. 'ollama:llama3.2:3b' or 'llama3.2:3b').
                    If omitted, request.model is evaluated as target or profile.
            profile_name: Optional routing profile name.
            request_id: Optional correlation ID for tracing.

        Returns:
            Tuple of (ChatCompletionResponse, RoutingDecisionEvent).

        Raises:
            ModelNotFoundError: Target model or profile cannot be resolved.
            UnsupportedCapabilityError: Model does not support requested capability.
            ProviderError: Non-retryable error, explicit failure, or failover exhausted.
        """
        start_time = self._clock()
        failover_history: list[FailoverAttempt] = []

        # Determine target and routing mode
        effective_target = target or request.model
        parsed_target: TargetResolution | None = None
        profile: RoutingProfile | None = None

        if profile_name is not None:
            profile = self.get_profile(profile_name)
            if profile is None:
                raise ModelNotFoundError(
                    f"Routing profile {profile_name!r} not found",
                    provider_id="routing",
                )
            routing_mode = "profile"
            requested_label = f"profile:{profile_name}"
            is_explicit = False
            candidates = self._select_profile_candidates(profile, request)
            max_retries = profile.max_retries
        else:
            # Check if effective_target matches a registered profile name
            if effective_target in self._profiles:
                profile = self._profiles[effective_target]
                routing_mode = "profile"
                requested_label = f"profile:{effective_target}"
                is_explicit = False
                candidates = self._select_profile_candidates(profile, request)
                max_retries = profile.max_retries
            else:
                parsed_target = self._resolver.parse_target(effective_target)
                is_explicit = parsed_target.is_explicit
                routing_mode = "explicit" if is_explicit else "model_id"
                requested_label = effective_target
                candidates = self._resolver.resolve_candidates(request, target=effective_target)
                # Explicit deployment requests NEVER failover to another deployment
                max_retries = 0 if is_explicit else 2

        # Filter out candidates currently in cooldown (unless all are in cooldown)
        active_candidates: list[CatalogEntry] = []
        cooldown_candidates: list[CatalogEntry] = []

        for cand in candidates:
            if self._cooldown.is_in_cooldown(cand.composite_id):
                cooldown_candidates.append(cand)
            else:
                active_candidates.append(cand)

        # If all candidates are in cooldown, raise RoutingExhaustedError
        candidates_to_try = active_candidates if active_candidates else []
        if not candidates_to_try:
            total_duration_ms = (self._clock() - start_time) * 1000.0
            event = RoutingDecisionEvent(
                request_id=request_id,
                routing_mode=routing_mode,
                requested_target=requested_label,
                profile_name=profile.name if profile else None,
                attempts=0,
                failover_history=[],
                success=False,
                latency_ms=total_duration_ms,
                error_category=ErrorCategory.UNAVAILABLE.value,
                error_message="All candidate deployments are temporarily in cooldown",
            )
            raise RoutingExhaustedError(
                f"All candidate deployments for {requested_label!r} are currently in cooldown",
                details={
                    "cooldown_candidates": [c.composite_id for c in cooldown_candidates],
                },
            )

        # Bounded execution loop
        max_attempts = min(len(candidates_to_try), max_retries + 1)
        last_error: ProviderError | None = None
        attempt_number = 0

        for candidate in candidates_to_try[:max_attempts]:
            attempt_number += 1
            attempt_start = self._clock()

            adapter = self._registry.get(candidate.provider_id)
            if adapter is None:
                err = ModelNotFoundError(
                    f"Provider {candidate.provider_id!r} is not registered",
                    provider_id=candidate.provider_id,
                )
                failover_history.append(
                    FailoverAttempt(
                        attempt_number=attempt_number,
                        composite_id=candidate.composite_id,
                        provider_id=candidate.provider_id,
                        model_id=candidate.model_id,
                        success=False,
                        error_category=err.category.value,
                        error_message=err.message,
                        is_retryable=False,
                        latency_ms=(self._clock() - attempt_start) * 1000.0,
                    )
                )
                last_error = err
                break

            # Execute with candidate-specific model ID
            cand_request = request.model_copy(update={"model": candidate.model_id})
            ctx = self._catalog.get_provider_context(candidate.provider_id)

            try:
                response = await adapter.complete_chat(ctx, cand_request)
                cand_duration = (self._clock() - attempt_start) * 1000.0
                total_duration = (self._clock() - start_time) * 1000.0

                # Clear failures on success
                self._cooldown.record_success(candidate.composite_id)

                failover_history.append(
                    FailoverAttempt(
                        attempt_number=attempt_number,
                        composite_id=candidate.composite_id,
                        provider_id=candidate.provider_id,
                        model_id=candidate.model_id,
                        success=True,
                        latency_ms=cand_duration,
                    )
                )

                # Extract token usage if available without inventing numbers
                p_tok = response.usage.prompt_tokens if response.usage else None
                c_tok = response.usage.completion_tokens if response.usage else None
                t_tok = response.usage.total_tokens if response.usage else None

                event = RoutingDecisionEvent(
                    request_id=request_id,
                    routing_mode=routing_mode,
                    requested_target=requested_label,
                    profile_name=profile.name if profile else None,
                    selected_composite_id=candidate.composite_id,
                    selected_provider_id=candidate.provider_id,
                    selected_model_id=candidate.model_id,
                    attempts=attempt_number,
                    failover_history=failover_history,
                    success=True,
                    latency_ms=total_duration,
                    prompt_tokens=p_tok,
                    completion_tokens=c_tok,
                    total_tokens=t_tok,
                )

                logger.info(
                    "Routing decision fulfilled",
                    routing_mode=routing_mode,
                    target=requested_label,
                    selected=candidate.composite_id,
                    attempts=attempt_number,
                    latency_ms=round(total_duration, 2),
                )
                return response, event

            except ProviderError as exc:
                cand_duration = (self._clock() - attempt_start) * 1000.0
                self._cooldown.record_failure(candidate.composite_id, exc)

                failover_history.append(
                    FailoverAttempt(
                        attempt_number=attempt_number,
                        composite_id=candidate.composite_id,
                        provider_id=candidate.provider_id,
                        model_id=candidate.model_id,
                        success=False,
                        error_category=exc.category.value,
                        error_message=exc.message,
                        is_retryable=exc.is_retryable,
                        latency_ms=cand_duration,
                    )
                )
                last_error = exc

                # Rule 1: Explicit requests NEVER silently failover to another deployment
                if is_explicit:
                    logger.warning(
                        "Explicit deployment failed; will not failover",
                        deployment=candidate.composite_id,
                        error=exc.message,
                    )
                    break

                # Rule 2: Non-retryable errors abort immediately (no failover)
                if not exc.is_retryable:
                    logger.warning(
                        "Encountered non-retryable provider error; aborting failover",
                        deployment=candidate.composite_id,
                        category=exc.category.value,
                        error=exc.message,
                    )
                    break

                # Rule 3: Retryable error, log failover transition if candidates remain
                logger.warning(
                    "Retryable provider error; evaluating next failover candidate",
                    deployment=candidate.composite_id,
                    attempt=attempt_number,
                    error=exc.message,
                )

        # If loop finished without returning, failover was exhausted or aborted
        total_duration = (self._clock() - start_time) * 1000.0
        final_category = (
            last_error.category.value if last_error else ErrorCategory.UNAVAILABLE.value
        )
        final_message = last_error.message if last_error else "Failover exhausted with no response"

        event = RoutingDecisionEvent(
            request_id=request_id,
            routing_mode=routing_mode,
            requested_target=requested_label,
            profile_name=profile.name if profile else None,
            attempts=attempt_number,
            failover_history=failover_history,
            success=False,
            latency_ms=total_duration,
            error_category=final_category,
            error_message=final_message,
        )

        logger.error(
            "Routing failed",
            routing_mode=routing_mode,
            target=requested_label,
            attempts=attempt_number,
            error=final_message,
        )

        if last_error is not None:
            raise last_error

        raise RoutingExhaustedError(
            f"All candidates exhausted for {requested_label!r}",
            details={"attempts": attempt_number},
        )


# Module-level default routing engine instance
default_engine = RoutingEngine()
