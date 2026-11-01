"""Deterministic unit and integration tests for FreeFlow AI Management API (/api).

Tests all 6 management endpoints:
1. GET /api/providers
2. POST /api/providers/{provider_id}/test
3. GET /api/catalog
4. POST /api/catalog/refresh
5. GET /api/profiles
6. GET /api/diagnostics

Validates Bearer authentication, sanitized error reporting, stale-model tracking,
custom routing profile exposure, and zero secret leakage.
"""

from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient

import backend.main as main_module
from backend.catalog.service import ModelCatalog
from backend.config import Settings
from backend.db.connection import DatabaseManager
from backend.db.repositories import CatalogRepository
from backend.main import app
from backend.providers.base import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ConnectionHealth,
    ModelCapability,
    ProviderAdapter,
    ProviderContext,
    ProviderModel,
)
from backend.providers.registry import ProviderRegistry
from backend.routing.engine import RoutingEngine
from backend.routing.models import RoutingProfile

TEST_MANAGEMENT_TOKEN = "mgmt-token-super-secret-xyz987"


class ControllableMockAdapter(ProviderAdapter):
    """Controllable adapter for management API testing."""

    def __init__(
        self,
        provider_id: str,
        models: list[ProviderModel] | None = None,
        *,
        healthy: bool = True,
        latency_ms: float = 15.2,
        error_message: str | None = None,
    ) -> None:
        self._provider_id = provider_id
        self._models = models or []
        self._healthy = healthy
        self._latency_ms = latency_ms
        self._error_message = error_message
        self.list_called = False

    @property
    def adapter_id(self) -> str:
        return self._provider_id

    async def list_models(self, context: ProviderContext) -> list[ProviderModel]:
        self.list_called = True
        if not self._healthy and self._error_message:
            raise RuntimeError(self._error_message)
        return self._models

    async def test_connection(self, context: ProviderContext) -> ConnectionHealth:
        return ConnectionHealth(
            healthy=self._healthy,
            message=self._error_message or ("Connected" if self._healthy else "Failed"),
            latency_ms=self._latency_ms,
        )

    async def complete_chat(
        self,
        context: ProviderContext,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        raise NotImplementedError


@pytest.fixture
def mgmt_setup(tmp_path: Path, monkeypatch):
    """Configures isolated database, catalog, registry, engine, and authenticated client."""
    monkeypatch.setenv("FREEFLOW_API_TOKEN", TEST_MANAGEMENT_TOKEN)
    db_file = str(tmp_path / "mgmt_test.db")
    monkeypatch.setenv("FREEFLOW_DB_PATH", db_file)

    original_settings = main_module.settings
    main_module.settings = Settings()

    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.initialize()
    repo = CatalogRepository(db_mgr)

    reg = ProviderRegistry()
    mock_model = ProviderModel(
        id="mock-model-1",
        provider_id="mock",
        display_name="Mock Model 1",
        capabilities=ModelCapability(
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
            context_window=8192,
        ),
        is_local=False,
    )
    multi_colon_model = ProviderModel(
        id="deepseek-r1:7b:q4_k_m",
        provider_id="ollama",
        display_name="DeepSeek R1 Quantized",
        capabilities=ModelCapability(
            supports_streaming=True,
            supports_tools=False,
            supports_vision=False,
            context_window=None,  # Unknown context window
        ),
        is_local=True,
    )

    mock_adapter = ControllableMockAdapter("mock", [mock_model], healthy=True, latency_ms=12.5)
    ollama_adapter = ControllableMockAdapter(
        "ollama", [multi_colon_model], healthy=True, latency_ms=8.0
    )
    failing_adapter = ControllableMockAdapter(
        "failing", [], healthy=False, latency_ms=50.0, error_message="Connect failed to server"
    )

    reg.register(mock_adapter)
    reg.register(ollama_adapter)
    reg.register(failing_adapter)

    cat = ModelCatalog(registry=reg, repository=repo)
    cat.set_provider_context(
        "mock",
        ProviderContext(base_url="https://api.mock.test", api_key="secret-key-1234"),
    )
    cat.set_provider_context(
        "ollama",
        ProviderContext(base_url="http://127.0.0.1:11434"),
    )

    engine = RoutingEngine(catalog=cat, registry=reg)
    engine.register_profile(
        RoutingProfile(
            name="coding_custom",
            description="Custom profile for coding",
            candidates=["ollama:deepseek-r1:7b:q4_k_m", "mock:mock-model-1"],
            max_retries=3,
            timeout_seconds=45.0,
        )
    )

    # Attach to app state
    app.state.db_manager = db_mgr
    app.state.catalog_repo = repo
    app.state.registry = reg
    app.state.catalog = cat
    app.state.routing_engine = engine

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {TEST_MANAGEMENT_TOKEN}"}

    try:
        yield {
            "client": client,
            "headers": headers,
            "catalog": cat,
            "registry": reg,
            "engine": engine,
            "db_mgr": db_mgr,
            "mock_adapter": mock_adapter,
            "ollama_adapter": ollama_adapter,
            "failing_adapter": failing_adapter,
        }
    finally:
        main_module.settings = original_settings
        app.state.catalog = None
        app.state.routing_engine = None
        app.state.registry = None
        app.state.db_manager = None
        app.state.catalog_repo = None
        db_mgr.close()


# ============================================================================
# 1. Authentication Tests for Management Routes
# ============================================================================


@pytest.mark.parametrize(
    "method,endpoint,payload",
    [
        ("GET", "/api/providers", None),
        ("POST", "/api/providers/mock/test", None),
        ("GET", "/api/catalog", None),
        ("POST", "/api/catalog/refresh", {}),
        ("GET", "/api/profiles", None),
        ("GET", "/api/diagnostics", None),
    ],
)
def test_management_routes_reject_unauthenticated(mgmt_setup, method, endpoint, payload):
    """All 6 management endpoints must reject missing or invalid tokens with HTTP 401."""
    client: TestClient = mgmt_setup["client"]

    # 1. Missing Authorization header
    if payload is not None:
        res1 = client.request(method, endpoint, json=payload)
    else:
        res1 = client.request(method, endpoint)
    assert res1.status_code == status.HTTP_401_UNAUTHORIZED
    assert "error" in res1.json()

    # 2. Invalid Bearer token
    invalid_headers = {"Authorization": "Bearer wrong-token-value"}
    if payload is not None:
        res2 = client.request(method, endpoint, headers=invalid_headers, json=payload)
    else:
        res2 = client.request(method, endpoint, headers=invalid_headers)
    assert res2.status_code == status.HTTP_401_UNAUTHORIZED

    # 3. Non-Bearer authorization scheme
    basic_headers = {"Authorization": "Basic dXNlcjpwYXNz"}
    if payload is not None:
        res3 = client.request(method, endpoint, headers=basic_headers, json=payload)
    else:
        res3 = client.request(method, endpoint, headers=basic_headers)
    assert res3.status_code == status.HTTP_401_UNAUTHORIZED


def test_management_routes_never_echo_token_or_secret(mgmt_setup):
    """Secret tokens must never appear in response payloads or logs."""
    client: TestClient = mgmt_setup["client"]
    bad_token = "VERY_CONFIDENTIAL_TOKEN_LEAK_CHECK"
    res = client.get("/api/providers", headers={"Authorization": f"Bearer {bad_token}"})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    assert bad_token not in res.text


# ============================================================================
# 2. Provider Endpoints Tests
# ============================================================================


def test_list_providers_success(mgmt_setup):
    """GET /api/providers accurately lists registered adapters with zero secret leakage."""
    client: TestClient = mgmt_setup["client"]
    headers = mgmt_setup["headers"]
    mock_adapter: ControllableMockAdapter = mgmt_setup["mock_adapter"]

    res = client.get("/api/providers", headers=headers)
    assert res.status_code == status.HTTP_200_OK

    data = res.json()["data"]
    provider_ids = [p["id"] for p in data]
    assert provider_ids == ["failing", "mock", "ollama"]

    # Check mock provider
    mock_info = next(p for p in data if p["id"] == "mock")
    assert mock_info["base_url"] == "https://api.mock.test"
    assert mock_info["has_credential"] is True
    assert mock_info["local"] is False
    # Ensure raw secret key is NOT present
    assert "secret-key-1234" not in res.text

    # Check ollama provider
    ollama_info = next(p for p in data if p["id"] == "ollama")
    assert ollama_info["base_url"] == "http://127.0.0.1:11434"
    assert ollama_info["has_credential"] is False
    assert ollama_info["local"] is True

    # Ensure list_models was NOT called as a side effect
    assert mock_adapter.list_called is False


def test_test_provider_connection_healthy(mgmt_setup):
    """POST /api/providers/{provider_id}/test returns healthy status and latency."""
    client: TestClient = mgmt_setup["client"]
    headers = mgmt_setup["headers"]

    res = client.post("/api/providers/mock/test", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    body = res.json()
    assert body["provider_id"] == "mock"
    assert body["status"] == "healthy"
    assert body["latency_ms"] == 12.5
    assert body["error"] is None


def test_test_provider_connection_unhealthy(mgmt_setup):
    """POST /api/providers/{provider_id}/test returns unhealthy status and sanitized error."""
    client: TestClient = mgmt_setup["client"]
    headers = mgmt_setup["headers"]

    res = client.post("/api/providers/failing/test", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    body = res.json()
    assert body["provider_id"] == "failing"
    assert body["status"] == "unhealthy"
    assert body["error"] == "Connect failed to server"


def test_test_provider_connection_unknown_provider_returns_404(mgmt_setup):
    """POST /api/providers/{provider_id}/test returns 404 for unregistered provider."""
    client: TestClient = mgmt_setup["client"]
    headers = mgmt_setup["headers"]

    res = client.post("/api/providers/non_existent_provider/test", headers=headers)
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert "not registered" in res.json()["error"]["message"]


# ============================================================================
# 3. Model Catalog Endpoints Tests
# ============================================================================


@pytest.mark.anyio
async def test_get_catalog_and_refresh_workflow(mgmt_setup):
    """GET /api/catalog and POST /api/catalog/refresh handle active, stale, and colon tags."""
    client: TestClient = mgmt_setup["client"]
    headers = mgmt_setup["headers"]

    # 1. Trigger initial refresh
    refresh_res = client.post("/api/catalog/refresh", headers=headers, json={})
    assert refresh_res.status_code == status.HTTP_200_OK
    refresh_data = refresh_res.json()
    assert refresh_data["total_refreshed"] == 3
    assert refresh_data["successful_refreshes"] == 2
    assert refresh_data["failed_refreshes"] == 1

    # 2. Query catalog models
    cat_res = client.get("/api/catalog", headers=headers)
    assert cat_res.status_code == status.HTTP_200_OK
    models = cat_res.json()["data"]
    assert len(models) == 2

    comp_ids = [m["composite_id"] for m in models]
    assert "mock:mock-model-1" in comp_ids
    assert "ollama:deepseek-r1:7b:q4_k_m" in comp_ids

    # Verify multi-colon model details
    multi_col = next(m for m in models if m["composite_id"] == "ollama:deepseek-r1:7b:q4_k_m")
    assert multi_col["model_id"] == "deepseek-r1:7b:q4_k_m"
    assert multi_col["provider_id"] == "ollama"
    assert multi_col["is_local"] is True
    # Unknown context window remains None / null
    assert multi_col["capabilities"]["context_window"] is None
    assert multi_col["is_stale"] is False

    # 3. Test provider filtering query parameter
    filter_res = client.get("/api/catalog?provider_id=mock", headers=headers)
    assert filter_res.status_code == status.HTTP_200_OK
    filtered_models = filter_res.json()["data"]
    assert len(filtered_models) == 1
    assert filtered_models[0]["composite_id"] == "mock:mock-model-1"

    # 4. Refresh single provider
    single_res = client.post(
        "/api/catalog/refresh", headers=headers, json={"provider_id": "mock"}
    )
    assert single_res.status_code == status.HTTP_200_OK
    single_data = single_res.json()
    assert single_data["total_refreshed"] == 1
    assert single_data["successful_refreshes"] == 1

    # 5. Refresh unknown provider returns 404
    unknown_res = client.post(
        "/api/catalog/refresh", headers=headers, json={"provider_id": "ghost"}
    )
    assert unknown_res.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# 4. Routing Profiles Endpoint Tests
# ============================================================================


def test_list_profiles_includes_builtin_and_custom(mgmt_setup):
    """GET /api/profiles returns all built-in profiles and custom registered profiles."""
    client: TestClient = mgmt_setup["client"]
    headers = mgmt_setup["headers"]

    res = client.get("/api/profiles", headers=headers)
    assert res.status_code == status.HTTP_200_OK

    data = res.json()["data"]
    profile_names = [p["name"] for p in data]

    # Built-in profiles
    assert "default" in profile_names
    assert "coding" in profile_names
    assert "fast" in profile_names
    assert "reasoning" in profile_names

    # Custom profile
    assert "coding_custom" in profile_names
    custom = next(p for p in data if p["name"] == "coding_custom")
    assert custom["candidates"] == ["ollama:deepseek-r1:7b:q4_k_m", "mock:mock-model-1"]
    assert custom["max_retries"] == 3
    assert custom["timeout_seconds"] == 45.0


# ============================================================================
# 5. Diagnostics Endpoint Tests
# ============================================================================


def test_get_diagnostics_normal_mode(mgmt_setup):
    """GET /api/diagnostics provides sanitized gateway and SQLite WAL metrics."""
    client: TestClient = mgmt_setup["client"]
    headers = mgmt_setup["headers"]

    res = client.get("/api/diagnostics", headers=headers)
    assert res.status_code == status.HTTP_200_OK

    body = res.json()
    assert body["status"] == "ok"
    assert body["database"]["available"] is True
    assert body["database"]["degraded"] is False
    assert body["database"]["mode"] == "wal"
    assert body["database"]["journal_mode"] == "wal"
    assert body["registered_providers_count"] == 3
    assert body["routing_profiles_count"] == 5  # 4 built-in + 1 custom
    assert "token" not in res.text
    assert "secret" not in res.text


def test_get_diagnostics_degraded_mode(mgmt_setup):
    """GET /api/diagnostics accurately and safely reports degraded in-memory mode."""
    client: TestClient = mgmt_setup["client"]
    headers = mgmt_setup["headers"]
    db_mgr: DatabaseManager = mgmt_setup["db_mgr"]

    # Force degraded mode on DatabaseManager
    db_mgr.is_degraded = True
    db_mgr.degraded_reason = "Disk full writing to C:\\FreeFlow\\data.db with token=xyz"

    res = client.get("/api/diagnostics", headers=headers)
    assert res.status_code == status.HTTP_200_OK

    body = res.json()
    assert body["database"]["degraded"] is True
    assert body["database"]["mode"] == "in_memory_fallback"
    # Ensure error reason is sanitized (paths and tokens redacted)
    assert "xyz" not in body["database"]["reason"]
    assert "[REDACTED]" in body["database"]["reason"]
    assert "[PATH]" in body["database"]["reason"]
