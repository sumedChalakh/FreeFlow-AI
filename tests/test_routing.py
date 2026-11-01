"""Comprehensive unit tests for FreeFlow AI Routing Engine and Automatic Failover.

Tests colon-safe resolution, explicit non-fallback rules, capability filtering,
health tracking, cooldown windows, bounded failover, non-retryable aborts,
concurrency safety, and telemetry privacy.
"""

import asyncio
from typing import Any

import pytest

from backend.catalog.models import CatalogEntry
from backend.catalog.service import ModelCatalog
from backend.providers.base import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ConnectionHealth,
    ModelCapability,
    ProviderAdapter,
    ProviderContext,
    ProviderModel,
    UsageInfo,
)
from backend.providers.errors import (
    AuthenticationError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    UnsupportedCapabilityError,
)
from backend.providers.registry import ProviderRegistry
from backend.routing.cooldown import CooldownTracker
from backend.routing.engine import RoutingEngine, RoutingExhaustedError
from backend.routing.models import RoutingProfile
from backend.routing.resolver import ModelResolver


class ControllableMockAdapter(ProviderAdapter):
    """Configurable mock adapter for deterministic routing and failover testing."""

    def __init__(
        self,
        provider_id: str,
        models: list[ProviderModel],
        responses: dict[str, Any] | None = None,
    ) -> None:
        self._provider_id = provider_id
        self._models = models
        self._responses = responses or {}
        self.call_count: int = 0
        self.calls: list[str] = []

    @property
    def adapter_id(self) -> str:
        return self._provider_id

    async def list_models(self, context: ProviderContext) -> list[ProviderModel]:
        return self._models

    async def test_connection(self, context: ProviderContext) -> ConnectionHealth:
        return ConnectionHealth(healthy=True)

    async def complete_chat(
        self,
        context: ProviderContext,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        self.call_count += 1
        self.calls.append(request.model)

        behavior = self._responses.get(request.model)
        if isinstance(behavior, Exception):
            raise behavior

        return ChatCompletionResponse(
            id=f"resp-{self._provider_id}-{self.call_count}",
            provider_id=self._provider_id,
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=f"Response from {self._provider_id}:{request.model}",
                    ),
                    finish_reason="stop",
                )
            ],
            usage=UsageInfo(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )


@pytest.fixture
def simulated_environment():
    """Sets up a clean registry, catalog, and adapters for routing tests."""
    reg = ProviderRegistry()
    cat = ModelCatalog(registry=reg)

    # Provider 1: Ollama with colon-containing model tags
    ollama_models = [
        ProviderModel(
            id="llama3.2:3b",
            provider_id="ollama",
            display_name="Llama 3.2 3B",
            capabilities=ModelCapability(supports_streaming=True, supports_tools=True),
            is_local=True,
        ),
        ProviderModel(
            id="qwen2.5-coder:7b",
            provider_id="ollama",
            display_name="Qwen 2.5 Coder 7B",
            capabilities=ModelCapability(supports_streaming=True, supports_tools=False),
            is_local=True,
        ),
    ]
    ollama_adapter = ControllableMockAdapter("ollama", ollama_models)
    reg.register(ollama_adapter)

    # Provider 2: Mock provider with general and failing models
    mock_models = [
        ProviderModel(
            id="general-chat",
            provider_id="mock",
            display_name="Mock General Chat",
            capabilities=ModelCapability(supports_streaming=True, supports_tools=True),
            is_local=False,
        ),
        ProviderModel(
            id="legacy-nostream",
            provider_id="mock",
            display_name="Legacy No-Stream",
            capabilities=ModelCapability(supports_streaming=False, supports_tools=False),
            is_local=False,
        ),
    ]
    mock_adapter = ControllableMockAdapter("mock", mock_models)
    reg.register(mock_adapter)

    # Populate catalog entries synchronously
    for m in ollama_models:
        cat._entries[f"{m.provider_id}:{m.id}"] = CatalogEntry.from_provider_model(m)
    for m in mock_models:
        cat._entries[f"{m.provider_id}:{m.id}"] = CatalogEntry.from_provider_model(m)

    return {
        "registry": reg,
        "catalog": cat,
        "ollama_adapter": ollama_adapter,
        "mock_adapter": mock_adapter,
    }


# ============================================================================
# Priority 1: Concurrency Safety
# ============================================================================


@pytest.mark.anyio
async def test_concurrent_catalog_refresh_safety():
    """Verify concurrent refresh operations do not raise RuntimeError or corrupt state."""
    reg = ProviderRegistry()
    cat = ModelCatalog(registry=reg)

    models_a = [
        ProviderModel(id=f"mod-a-{i}", provider_id="prov_a", display_name=f"Model A {i}")
        for i in range(15)
    ]
    models_b = [
        ProviderModel(id=f"mod-b-{i}", provider_id="prov_b", display_name=f"Model B {i}")
        for i in range(15)
    ]

    adapter_a = ControllableMockAdapter("prov_a", models_a)
    adapter_b = ControllableMockAdapter("prov_b", models_b)
    reg.register(adapter_a)
    reg.register(adapter_b)

    # Launch overlapping concurrent refreshes across both providers
    tasks = [
        cat.refresh_provider("prov_a"),
        cat.refresh_provider("prov_b"),
        cat.refresh_provider("prov_a"),
        cat.refresh_provider("prov_b"),
    ]
    results = await asyncio.gather(*tasks)

    assert all(r.success for r in results)
    assert len(cat.list_entries()) == 30


# ============================================================================
# Priority 2: Colon-Safe Target Resolution
# ============================================================================


def test_colon_safe_resolution(simulated_environment):
    """Verify composite-ID resolution preserves colons and identifies providers."""
    resolver = ModelResolver(
        catalog=simulated_environment["catalog"],
        registry=simulated_environment["registry"],
    )

    # Case 1: Registered provider prefix with colon in model ID
    res1 = resolver.parse_target("ollama:llama3.2:3b")
    assert res1.is_explicit is True
    assert res1.provider_id == "ollama"
    assert res1.model_id == "llama3.2:3b"
    assert res1.composite_id == "ollama:llama3.2:3b"

    # Case 2: Unprefixed model ID containing colons (where prefix is NOT a registered provider)
    res2 = resolver.parse_target("llama3.2:3b")
    assert res2.is_explicit is False
    assert res2.model_id == "llama3.2:3b"

    # Case 3: Registered provider with plain model ID
    res3 = resolver.parse_target("mock:general-chat")
    assert res3.is_explicit is True
    assert res3.provider_id == "mock"
    assert res3.model_id == "general-chat"
    assert res3.composite_id == "mock:general-chat"

    # Case 4: Non-existent provider prefix
    res4 = resolver.parse_target("unknown_provider:some-model")
    assert res4.is_explicit is False
    assert res4.model_id == "unknown_provider:some-model"


# ============================================================================
# Priority 5: Explicit Deployment Never Falls Back
# ============================================================================


@pytest.mark.anyio
async def test_explicit_deployment_success(simulated_environment):
    """Verify an explicit deployment request routes directly to the requested backend."""
    engine = RoutingEngine(
        catalog=simulated_environment["catalog"],
        registry=simulated_environment["registry"],
    )

    req = ChatCompletionRequest(
        model="ollama:llama3.2:3b",
        messages=[ChatMessage(role="user", content="Hello")],
    )

    response, event = await engine.complete_chat(req)

    assert response.provider_id == "ollama"
    assert response.model == "llama3.2:3b"
    assert event.routing_mode == "explicit"
    assert event.selected_composite_id == "ollama:llama3.2:3b"
    assert event.attempts == 1
    assert event.success is True
    assert simulated_environment["ollama_adapter"].call_count == 1
    assert simulated_environment["mock_adapter"].call_count == 0


@pytest.mark.anyio
async def test_explicit_deployment_never_silently_falls_back(simulated_environment):
    """Verify that an explicit deployment error (even retryable) never falls back."""
    ollama_adapter: ControllableMockAdapter = simulated_environment["ollama_adapter"]
    ollama_adapter._responses["llama3.2:3b"] = ProviderTimeoutError(
        "Ollama timed out",
        provider_id="ollama",
    )

    engine = RoutingEngine(
        catalog=simulated_environment["catalog"],
        registry=simulated_environment["registry"],
    )

    req = ChatCompletionRequest(
        model="ollama:llama3.2:3b",
        messages=[ChatMessage(role="user", content="Hello")],
    )

    with pytest.raises(ProviderTimeoutError) as exc_info:
        await engine.complete_chat(req)

    assert exc_info.value.provider_id == "ollama"
    # Even though mock:general-chat was healthy in catalog, mock adapter was NEVER called
    assert simulated_environment["mock_adapter"].call_count == 0
    assert ollama_adapter.call_count == 1


# ============================================================================
# Priority 3 & 4: Profiles, Capability Filtering, Bounded Failover
# ============================================================================


@pytest.mark.anyio
async def test_profile_failover_on_retryable_error(simulated_environment):
    """Verify that a profile automatically fails over to the next candidate on a retryable error."""
    # Candidate 1: Ollama fails with retryable ProviderUnavailableError
    ollama_adapter: ControllableMockAdapter = simulated_environment["ollama_adapter"]
    ollama_adapter._responses["llama3.2:3b"] = ProviderUnavailableError(
        "Local daemon restarting",
        provider_id="ollama",
    )

    engine = RoutingEngine(
        catalog=simulated_environment["catalog"],
        registry=simulated_environment["registry"],
    )

    profile = RoutingProfile(
        name="test_failover",
        candidates=["ollama:llama3.2:3b", "mock:general-chat"],
        max_retries=2,
    )
    engine.register_profile(profile)

    req = ChatCompletionRequest(
        model="test_failover",
        messages=[ChatMessage(role="user", content="Hello")],
    )

    response, event = await engine.complete_chat(req, profile_name="test_failover")

    assert response.provider_id == "mock"
    assert response.model == "general-chat"
    assert event.attempts == 2
    assert event.success is True
    assert event.selected_composite_id == "mock:general-chat"
    assert len(event.failover_history) == 2
    assert event.failover_history[0].success is False
    assert event.failover_history[0].is_retryable is True
    assert event.failover_history[1].success is True


@pytest.mark.anyio
async def test_non_retryable_error_aborts_immediately(simulated_environment):
    """Verify non-retryable errors (auth, bad request) fail fast without failover."""
    ollama_adapter: ControllableMockAdapter = simulated_environment["ollama_adapter"]
    # AuthenticationError is non-retryable
    ollama_adapter._responses["llama3.2:3b"] = AuthenticationError(
        "Bad credentials",
        provider_id="ollama",
    )

    engine = RoutingEngine(
        catalog=simulated_environment["catalog"],
        registry=simulated_environment["registry"],
    )

    profile = RoutingProfile(
        name="test_abort",
        candidates=["ollama:llama3.2:3b", "mock:general-chat"],
        max_retries=2,
    )
    engine.register_profile(profile)

    req = ChatCompletionRequest(
        model="test_abort",
        messages=[ChatMessage(role="user", content="Hello")],
    )

    with pytest.raises(AuthenticationError):
        await engine.complete_chat(req, profile_name="test_abort")

    # Mock adapter must NOT have been called
    assert simulated_environment["mock_adapter"].call_count == 0
    assert ollama_adapter.call_count == 1


@pytest.mark.anyio
async def test_capability_filtering_excludes_incompatible_models(simulated_environment):
    """Verify models lacking requested capabilities are filtered out of candidate selection."""
    engine = RoutingEngine(
        catalog=simulated_environment["catalog"],
        registry=simulated_environment["registry"],
    )

    # mock:legacy-nostream has supports_streaming=False
    # Requesting stream=True on an explicit deployment that lacks it must fail
    req_stream = ChatCompletionRequest(
        model="mock:legacy-nostream",
        messages=[ChatMessage(role="user", content="Hello")],
        stream=True,
    )

    with pytest.raises(UnsupportedCapabilityError):
        await engine.complete_chat(req_stream)


@pytest.mark.anyio
async def test_retry_budget_ceiling(simulated_environment):
    """Verify failover stops when max_retries budget is exhausted."""
    ollama_adapter: ControllableMockAdapter = simulated_environment["ollama_adapter"]
    mock_adapter: ControllableMockAdapter = simulated_environment["mock_adapter"]

    ollama_adapter._responses["llama3.2:3b"] = ProviderTimeoutError("timeout", provider_id="ollama")
    mock_adapter._responses["general-chat"] = ProviderTimeoutError("timeout", provider_id="mock")

    engine = RoutingEngine(
        catalog=simulated_environment["catalog"],
        registry=simulated_environment["registry"],
    )

    # Budget max_retries = 1 allows initial attempt + 1 retry = 2 attempts total
    profile = RoutingProfile(
        name="budget_test",
        candidates=["ollama:llama3.2:3b", "mock:general-chat"],
        max_retries=1,
    )
    engine.register_profile(profile)

    req = ChatCompletionRequest(
        model="budget_test",
        messages=[ChatMessage(role="user", content="Hello")],
    )

    with pytest.raises(ProviderTimeoutError):
        await engine.complete_chat(req, profile_name="budget_test")

    assert ollama_adapter.call_count == 1
    assert mock_adapter.call_count == 1


# ============================================================================
# Priority 3: Cooldown and Health Tracking
# ============================================================================


def test_cooldown_tracker_with_controlled_clock():
    """Verify consecutive failure tracking and cooldown expiration using a controlled clock."""
    current_time: float = 1000.0

    def mock_clock() -> float:
        return current_time

    tracker = CooldownTracker(failure_threshold=2, cooldown_seconds=30.0, clock=mock_clock)

    err = ProviderTimeoutError("timeout", provider_id="mock")

    # Failure 1: count is 1, not in cooldown
    entered = tracker.record_failure("mock:model1", err)
    assert entered is False
    assert tracker.is_in_cooldown("mock:model1") is False
    assert tracker.get_failure_count("mock:model1") == 1

    # Failure 2: reaches threshold 2, enters cooldown
    entered = tracker.record_failure("mock:model1", err)
    assert entered is True
    assert tracker.is_in_cooldown("mock:model1") is True
    assert tracker.get_cooldown_remaining("mock:model1") == 30.0

    # Advance clock by 15s: still in cooldown
    current_time += 15.0
    assert tracker.is_in_cooldown("mock:model1") is True
    assert tracker.get_cooldown_remaining("mock:model1") == 15.0

    # Advance clock past 30s: cooldown expired
    current_time += 16.0
    assert tracker.is_in_cooldown("mock:model1") is False
    assert tracker.get_cooldown_remaining("mock:model1") == 0.0

    # Success clears failure count
    tracker.record_success("mock:model1")
    assert tracker.get_failure_count("mock:model1") == 0


@pytest.mark.anyio
async def test_all_candidates_in_cooldown_raises_exhausted(simulated_environment):
    """Verify that when all profile candidates are in cooldown, RoutingExhaustedError is raised."""
    current_time: float = 1000.0

    def mock_clock() -> float:
        return current_time

    tracker = CooldownTracker(failure_threshold=1, cooldown_seconds=60.0, clock=mock_clock)
    tracker.record_failure(
        "ollama:llama3.2:3b",
        ProviderTimeoutError("timeout", provider_id="ollama"),
    )
    tracker.record_failure(
        "mock:general-chat",
        ProviderTimeoutError("timeout", provider_id="mock"),
    )

    engine = RoutingEngine(
        catalog=simulated_environment["catalog"],
        registry=simulated_environment["registry"],
        cooldown_tracker=tracker,
        clock=mock_clock,
    )

    profile = RoutingProfile(
        name="all_cooldown",
        candidates=["ollama:llama3.2:3b", "mock:general-chat"],
    )
    engine.register_profile(profile)

    req = ChatCompletionRequest(
        model="all_cooldown",
        messages=[ChatMessage(role="user", content="Hello")],
    )

    with pytest.raises(RoutingExhaustedError) as exc_info:
        await engine.complete_chat(req, profile_name="all_cooldown")

    assert "cooldown" in exc_info.value.message.lower()


# ============================================================================
# Priority 6: Telemetry Privacy
# ============================================================================


@pytest.mark.anyio
async def test_telemetry_does_not_leak_prompt_or_message_content(simulated_environment):
    """Verify telemetry records metadata and tokens without capturing prompt text."""
    engine = RoutingEngine(
        catalog=simulated_environment["catalog"],
        registry=simulated_environment["registry"],
    )

    secret_prompt = "CONFIDENTIAL_PAYLOAD_XYZ_12345"
    req = ChatCompletionRequest(
        model="mock:general-chat",
        messages=[ChatMessage(role="user", content=secret_prompt)],
    )

    response, event = await engine.complete_chat(req)

    event_dict = event.model_dump()
    event_str = str(event_dict)

    assert secret_prompt not in event_str
    assert event.success is True
    assert event.prompt_tokens == 10
    assert event.completion_tokens == 20
    assert event.total_tokens == 30
    assert event.latency_ms >= 0.0
