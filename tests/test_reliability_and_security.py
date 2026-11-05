"""Automated tests for Phase 8: Reliability, Security Hardening & Usability Audit.

Validates:
- Routing profile timeout enforcement on provider execution context.
- Adapter unexpected exception containment and automatic failover.
- Preservation and propagation of asyncio cancellation.
- Generic unhandled exception mapping to sanitized OpenAI 500 envelope.
- Input validation bounds for oversized models and roles.
- Comprehensive secret and filesystem path sanitization in management API.
- Lifespan graceful shutdown of registry adapters and database connections.
- Cooldown recovery after timeout window expiration.
- Keyboard navigation focus visibility in dashboard stylesheet.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from backend.api import register_error_handlers
from backend.catalog import CatalogEntry, ModelCatalog
from backend.db import DatabaseManager
from backend.main import app, lifespan
from backend.management.routes import sanitize_error
from backend.providers.base import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ModelCapability,
    ProviderAdapter,
    ProviderContext,
    ProviderModel,
)
from backend.providers.errors import ProviderUnavailableError
from backend.providers.registry import ProviderRegistry
from backend.routing.cooldown import CooldownTracker
from backend.routing.engine import RoutingEngine
from backend.routing.models import RoutingProfile


class CrashingAdapter(ProviderAdapter):
    """Adapter that crashes with an unexpected non-ProviderError exception."""

    def __init__(self, adapter_id: str, exc_to_raise: Exception) -> None:
        self._adapter_id = adapter_id
        self._exc = exc_to_raise

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    async def list_models(self, context: ProviderContext) -> list[ProviderModel]:
        return []

    async def test_connection(self, context: ProviderContext):
        from backend.providers.base import ConnectionHealth

        return ConnectionHealth(healthy=False, message="crashing")

    async def complete_chat(
        self, context: ProviderContext, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        raise self._exc


class TimeoutInspectingAdapter(ProviderAdapter):
    """Adapter that records the timeout_seconds from ProviderContext."""

    def __init__(self, adapter_id: str) -> None:
        self._adapter_id = adapter_id
        self.received_timeout: float | None = None

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    async def list_models(self, context: ProviderContext) -> list[ProviderModel]:
        return []

    async def test_connection(self, context: ProviderContext):
        from backend.providers.base import ConnectionHealth

        return ConnectionHealth(healthy=True)

    async def complete_chat(
        self, context: ProviderContext, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        self.received_timeout = context.timeout_seconds
        return ChatCompletionResponse(
            id="test-timeout-resp",
            provider_id=self.adapter_id,
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content="Timeout verified"),
                )
            ],
        )


class DummyCloseAdapter(ProviderAdapter):
    """Adapter tracking aclose() invocations during graceful shutdown."""

    def __init__(self, adapter_id: str) -> None:
        self._adapter_id = adapter_id
        self.closed = False

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    async def list_models(self, context: ProviderContext) -> list[ProviderModel]:
        return []

    async def test_connection(self, context: ProviderContext):
        from backend.providers.base import ConnectionHealth

        return ConnectionHealth(healthy=True)

    async def complete_chat(
        self, context: ProviderContext, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        return ChatCompletionResponse(
            id="resp",
            provider_id=self.adapter_id,
            model=request.model,
            choices=[ChatChoice(message=ChatMessage(role="assistant", content="ok"))],
        )

    async def aclose(self) -> None:
        self.closed = True


# ==============================================================================
# 1. Routing Engine Reliability Tests
# ==============================================================================


@pytest.mark.anyio
async def test_routing_engine_enforces_profile_timeout_override():
    """Verify profile timeout_seconds is applied to ProviderContext during completion."""
    registry = ProviderRegistry()
    inspecting_adapter = TimeoutInspectingAdapter(adapter_id="inspect-prov")
    registry.register(inspecting_adapter)

    catalog = ModelCatalog(registry=registry)
    catalog._entries["inspect-prov:fast-model"] = CatalogEntry(
        composite_id="inspect-prov:fast-model",
        provider_id="inspect-prov",
        model_id="fast-model",
        display_name="Fast Model",
        is_local=True,
        capabilities=ModelCapability(supports_streaming=False),
        is_stale=False,
    )
    # Default provider context has 30.0s timeout
    catalog.set_provider_context("inspect-prov", ProviderContext(timeout_seconds=30.0))

    engine = RoutingEngine(catalog=catalog, registry=registry)
    fast_profile = RoutingProfile(
        name="tight-timeout-profile",
        description="Profile with a strict 4.5s ceiling",
        candidates=["inspect-prov:fast-model"],
        timeout_seconds=4.5,
    )
    engine.register_profile(fast_profile)

    req = ChatCompletionRequest(
        model="tight-timeout-profile",
        messages=[ChatMessage(role="user", content="Hello")],
    )

    resp, event = await engine.complete_chat(req, profile_name="tight-timeout-profile")
    assert resp.choices[0].message.content == "Timeout verified"
    assert inspecting_adapter.received_timeout == 4.5
    assert event.success is True


@pytest.mark.anyio
async def test_routing_engine_contains_unexpected_adapter_exception_and_fails_over():
    """Verify non-ProviderError adapter crashes are caught, recorded, and trigger failover."""
    registry = ProviderRegistry()

    # Candidate 1 raises an unexpected raw RuntimeError (e.g. underlying transport bug)
    bad_adapter = CrashingAdapter("crash-prov", RuntimeError("Low-level OS socket error"))
    # Candidate 2 succeeds
    good_adapter = TimeoutInspectingAdapter("good-prov")
    registry.register(bad_adapter)
    registry.register(good_adapter)

    catalog = ModelCatalog(registry=registry)
    catalog._entries["crash-prov:model-a"] = CatalogEntry(
        composite_id="crash-prov:model-a",
        provider_id="crash-prov",
        model_id="model-a",
        display_name="Model A",
        is_local=False,
        capabilities=ModelCapability(),
        is_stale=False,
    )
    catalog._entries["good-prov:model-b"] = CatalogEntry(
        composite_id="good-prov:model-b",
        provider_id="good-prov",
        model_id="model-b",
        display_name="Model B",
        is_local=False,
        capabilities=ModelCapability(),
        is_stale=False,
    )

    engine = RoutingEngine(catalog=catalog, registry=registry)
    test_profile = RoutingProfile(
        name="resilient-profile",
        description="Profile testing failover on unexpected crashes",
        candidates=["crash-prov:model-a", "good-prov:model-b"],
        max_retries=1,
    )
    engine.register_profile(test_profile)

    req = ChatCompletionRequest(
        model="resilient-profile",
        messages=[ChatMessage(role="user", content="Test crash failover")],
    )

    resp, event = await engine.complete_chat(req, profile_name="resilient-profile")
    assert resp.choices[0].message.content == "Timeout verified"
    assert event.attempts == 2
    assert len(event.failover_history) == 2
    # Verify attempt 1 was captured cleanly
    assert event.failover_history[0].success is False
    assert "Low-level OS socket error" in (event.failover_history[0].error_message or "")
    # Verify attempt 2 succeeded
    assert event.failover_history[1].success is True
    assert event.selected_composite_id == "good-prov:model-b"


@pytest.mark.anyio
async def test_routing_engine_explicit_unexpected_exception_aborts():
    """Verify explicit deployment crashes with unexpected errors abort without failover."""
    registry = ProviderRegistry()
    bad_adapter = CrashingAdapter("crash-prov", ValueError("Corrupted buffer"))
    registry.register(bad_adapter)

    catalog = ModelCatalog(registry=registry)
    catalog._entries["crash-prov:model-a"] = CatalogEntry(
        composite_id="crash-prov:model-a",
        provider_id="crash-prov",
        model_id="model-a",
        display_name="Model A",
        is_local=False,
        capabilities=ModelCapability(),
        is_stale=False,
    )

    engine = RoutingEngine(catalog=catalog, registry=registry)

    req = ChatCompletionRequest(
        model="crash-prov:model-a",
        messages=[ChatMessage(role="user", content="Explicit test")],
    )

    with pytest.raises(ProviderUnavailableError) as exc_info:
        await engine.complete_chat(req, target="crash-prov:model-a")

    assert "Unexpected provider error" in str(exc_info.value)
    assert exc_info.value.provider_id == "crash-prov"


@pytest.mark.anyio
async def test_routing_engine_cancellation_propagates_unswallowed():
    """Verify asyncio.CancelledError is never swallowed and propagates up the call chain."""
    registry = ProviderRegistry()
    cancel_adapter = CrashingAdapter("cancel-prov", asyncio.CancelledError())
    registry.register(cancel_adapter)

    catalog = ModelCatalog(registry=registry)
    catalog._entries["cancel-prov:model-c"] = CatalogEntry(
        composite_id="cancel-prov:model-c",
        provider_id="cancel-prov",
        model_id="model-c",
        display_name="Model C",
        is_local=False,
        capabilities=ModelCapability(),
        is_stale=False,
    )

    engine = RoutingEngine(catalog=catalog, registry=registry)
    req = ChatCompletionRequest(
        model="cancel-prov:model-c",
        messages=[ChatMessage(role="user", content="Cancel test")],
    )

    with pytest.raises(asyncio.CancelledError):
        await engine.complete_chat(req, target="cancel-prov:model-c")


# ==============================================================================
# 2. API Security, Unhandled Exceptions & Validation Bounds
# ==============================================================================


def test_unhandled_server_exception_returns_sanitized_500_openai_envelope():
    """Verify unexpected 500 exceptions return standard OpenAI error shape without tracebacks."""
    test_app = FastAPI()
    register_error_handlers(test_app)

    @test_app.get("/trigger-crash")
    async def crash_endpoint():
        raise ZeroDivisionError("Simulated unexpected crash: integer division by zero")

    client = TestClient(test_app, raise_server_exceptions=False)
    res = client.get("/trigger-crash")
    assert res.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = res.json()
    assert "error" in data
    assert data["error"]["type"] == "api_error"
    assert data["error"]["code"] == "internal_server_error"
    # Never leak raw traceback, file paths, or division-by-zero detail
    assert "division by zero" not in data["error"]["message"].lower()
    assert (
        data["error"]["message"]
        == "An internal server error occurred while processing your request."
    )


def test_request_payload_validation_bounds_oversized_model(monkeypatch):
    """Verify request validation rejects model identifier exceeding max_length=256."""
    import backend.config as cfg
    import backend.main as main_mod

    monkeypatch.setattr(cfg.settings, "api_token", "test-token")
    monkeypatch.setattr(main_mod.settings, "api_token", "test-token")

    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}

    oversized_model = "m" * 300
    res = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": oversized_model,
            "messages": [{"role": "user", "content": "Hi"}],
        },
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    data = res.json()
    assert data["error"]["type"] == "invalid_request_error"
    assert data["error"]["code"] == "bad_request"
    assert "model" in data["error"]["message"]


def test_request_payload_validation_bounds_oversized_role(monkeypatch):
    """Verify request validation rejects participant role exceeding max_length=64."""
    import backend.config as cfg
    import backend.main as main_mod

    monkeypatch.setattr(cfg.settings, "api_token", "test-token")
    monkeypatch.setattr(main_mod.settings, "api_token", "test-token")

    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}

    oversized_role = "r" * 100
    res = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "default",
            "messages": [{"role": oversized_role, "content": "Hi"}],
        },
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    data = res.json()
    assert data["error"]["type"] == "invalid_request_error"
    assert data["error"]["code"] == "bad_request"
    assert "role" in data["error"]["message"]


# ==============================================================================
# 3. Management API Sanitization Tests
# ==============================================================================


def test_management_api_error_sanitization_comprehensive():
    """Verify sanitize_error eliminates all secrets, tokens, passwords, and file paths."""
    # Test tokens and keys
    raw_1 = "Failed with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 and key=sk-proj-12345"
    san_1 = sanitize_error(raw_1)
    assert "[REDACTED]" in san_1
    assert "eyJhbGci" not in san_1
    assert "sk-proj-12345" not in san_1

    # Test passwords and secrets
    raw_2 = "Connection failed: password: super_secret_pass and secret=top_secret_token"
    san_2 = sanitize_error(raw_2)
    assert "super_secret_pass" not in san_2
    assert "top_secret_token" not in san_2
    assert "[REDACTED]" in san_2

    # Test Windows filesystem paths
    raw_3 = r"Database error at E:\FreeFlow AI\backend\db\freeflow.db.corrupt"
    san_3 = sanitize_error(raw_3)
    assert "[PATH]" in san_3
    assert r"E:\FreeFlow" not in san_3

    # Test Unix filesystem paths
    raw_4 = "File missing at /var/run/secrets/credentials.json on server"
    san_4 = sanitize_error(raw_4)
    assert "[PATH]" in san_4
    assert "/var/run" not in san_4

    # Test truncation of excessively long error traces (>300 chars)
    raw_long = "Trace: " + ("x" * 400)
    san_long = sanitize_error(raw_long)
    assert len(san_long) <= 303
    assert san_long.endswith("...")


# ==============================================================================
# 4. Graceful Shutdown & Resource Cleanup
# ==============================================================================


@pytest.mark.anyio
async def test_graceful_shutdown_cleans_up_registry_and_db(tmp_path):
    """Verify lifespan shutdown cleanly executes registry.aclose() and db_mgr.close()."""
    test_db = str(tmp_path / "shutdown_test.db")
    test_app = FastAPI(lifespan=lifespan)

    with (
        patch("backend.main.settings.db_path", test_db),
        patch("backend.main.default_registry") as mock_registry,
    ):
        mock_registry.get.return_value = None
        mock_registry.list_adapters.return_value = []
        mock_registry.aclose = AsyncMock()

        async with lifespan(test_app):
            db_mgr = test_app.state.db_manager
            assert isinstance(db_mgr, DatabaseManager)
            assert db_mgr.is_initialized is True

        # Post-shutdown assertions
        mock_registry.aclose.assert_awaited_once()
        assert db_mgr.is_initialized is False
        assert db_mgr._conn is None


@pytest.mark.anyio
async def test_registry_aclose_calls_adapter_aclose():
    """Verify ProviderRegistry.aclose() closes all registered adapters."""
    reg = ProviderRegistry()
    adapter_1 = DummyCloseAdapter("dummy-1")
    adapter_2 = DummyCloseAdapter("dummy-2")
    reg.register(adapter_1)
    reg.register(adapter_2)

    await reg.aclose()
    assert adapter_1.closed is True
    assert adapter_2.closed is True


# ==============================================================================
# 5. Cooldown Recovery Verification
# ==============================================================================


def test_cooldown_recovery_after_expiry():
    """Verify candidate deployment recovers and exits cooldown after the window elapses."""
    clock_state = {"time": 1000.0}

    def mock_clock() -> float:
        return float(clock_state["time"])

    # Cooldown duration: 30s, threshold: 2 consecutive failures
    tracker = CooldownTracker(
        failure_threshold=2,
        cooldown_seconds=30.0,
        clock=mock_clock,
    )

    deployment_id = "test-prov:llama-7b"
    err = ProviderUnavailableError("Temporary downtime", provider_id="test-prov")

    # Failure 1: not in cooldown yet
    tracker.record_failure(deployment_id, err)
    assert tracker.is_in_cooldown(deployment_id) is False

    # Failure 2: reaches threshold -> enters cooldown
    tracker.record_failure(deployment_id, err)
    assert tracker.is_in_cooldown(deployment_id) is True

    # Advance clock by 15s (still within 30s window)
    clock_state["time"] += 15.0
    assert tracker.is_in_cooldown(deployment_id) is True

    # Advance clock past the 30s window (total 35s advanced)
    clock_state["time"] += 20.0
    assert tracker.is_in_cooldown(deployment_id) is False
    assert tracker.get_cooldown_remaining(deployment_id) == 0.0


# ==============================================================================
# 6. Dashboard Usability & Focus Visibility Styles
# ==============================================================================


def test_dashboard_css_focus_visible_keyboard_navigation():
    """Verify dashboard CSS provides explicit focus-visible rules for keyboard accessibility."""
    from backend.dashboard.routes import STATIC_DIR

    css_path = STATIC_DIR / "dashboard.css"
    assert css_path.exists()
    content = css_path.read_text(encoding="utf-8")

    assert ".nav-link:focus-visible" in content
    assert ".btn:focus-visible" in content
    assert "outline" in content
