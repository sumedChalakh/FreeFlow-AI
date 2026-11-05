"""Integration tests for FreeFlow AI Dashboard & Providers (P7-M2 & P7-M3).

Covers:
- GET /dashboard returns HTML application shell (200 OK)
- GET / redirects to /dashboard (307 Temporary Redirect)
- Static assets (dashboard.css, dashboard.js) are properly served
- Active navigation for Overview and Providers views
- Remaining future navigation items disabled with "Soon" badges
- Dedicated Providers view elements (#providers-view, #providers-cards-container)
- Provider connectivity test contract (healthy, unhealthy, 404, 401)
- Zero secret leakage in HTML, CSS, and JS
- Safe DOM rendering preventing script/HTML injection
- Explicit on-demand probing (no implicit probe on view render or refresh)
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.catalog.models import CatalogEntry
from backend.catalog.service import ModelCatalog
from backend.config import settings
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
from backend.routing.engine import RoutingEngine
from backend.routing.models import RoutingProfile


@pytest.fixture
def client():
    """Test client for dashboard routes."""
    return TestClient(app, follow_redirects=False)


class ControllableMockAdapter(ProviderAdapter):
    """Mock adapter with controllable probe and discovery results."""

    def __init__(
        self,
        adapter_id: str,
        healthy: bool = True,
        latency_ms: float = 15.0,
        msg: str | None = None,
        models: list[ProviderModel] | None = None,
        fail_discovery: bool = False,
    ):
        self._adapter_id = adapter_id
        self._healthy = healthy
        self._latency_ms = latency_ms
        self._msg = msg
        self._models = models if models is not None else []
        self._fail_discovery = fail_discovery
        self.probe_call_count = 0
        self.discovery_call_count = 0

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    async def list_models(self, context: ProviderContext) -> list[ProviderModel]:
        self.discovery_call_count += 1
        if self._fail_discovery:
            raise RuntimeError(f"Connection failed to {self._adapter_id} endpoint at [PATH]")
        return self._models

    async def test_connection(self, context: ProviderContext) -> ConnectionHealth:
        self.probe_call_count += 1
        return ConnectionHealth(
            healthy=self._healthy,
            latency_ms=self._latency_ms,
            message=self._msg,
        )

    async def complete_chat(
        self, context: ProviderContext, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        raise NotImplementedError()


# ============================================================================
# 1. Dashboard Routing & Asset Serving Tests
# ============================================================================


def test_get_dashboard_returns_html_success(client: TestClient):
    """GET /dashboard serves the HTML application shell with 200 OK."""
    response = client.get("/dashboard")
    assert response.status_code == status.HTTP_200_OK
    assert "text/html" in response.headers.get("content-type", "")
    content = response.text
    assert "<title>FreeFlow AI — Dashboard</title>" in content
    assert "FreeFlow AI" in content
    assert "Overview" in content
    assert "Providers" in content


def test_root_redirects_to_dashboard(client: TestClient):
    """GET / redirects traffic to /dashboard with HTTP 307."""
    response = client.get("/")
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers.get("location") == "/dashboard"


def test_dashboard_static_css_served(client: TestClient):
    """GET /dashboard/static/dashboard.css returns stylesheet with 200 OK."""
    response = client.get("/dashboard/static/dashboard.css")
    assert response.status_code == status.HTTP_200_OK
    content_type = response.headers.get("content-type", "")
    assert "text/css" in content_type
    assert "--color-bg-base" in response.text
    assert ".providers-cards-grid" in response.text


def test_dashboard_static_js_served(client: TestClient):
    """GET /dashboard/static/dashboard.js returns JavaScript controller with 200 OK."""
    response = client.get("/dashboard/static/dashboard.js")
    assert response.status_code == status.HTTP_200_OK
    content_type = response.headers.get("content-type", "")
    assert ("javascript" in content_type) or ("text/javascript" in content_type)
    assert "fetchDashboardData" in response.text
    assert "testProviderConnection" in response.text


# ============================================================================
# 2. Application Shell & Navigation Semantics Tests
# ============================================================================


def test_application_shell_navigation_structure(client: TestClient):
    """Sidebar navigation has active Overview, Providers, Catalog, Profiles, and Diagnostics."""
    response = client.get("/dashboard")
    assert response.status_code == status.HTTP_200_OK
    content = response.text

    # Overview item is present and has data-view="overview"
    assert 'id="nav-link-overview"' in content
    assert 'data-view="overview"' in content

    # Providers item is functional (not disabled, no 'Soon' badge)
    assert 'id="nav-link-providers"' in content
    assert 'data-view="providers"' in content

    # Model Catalog item is functional (not disabled, no 'Soon' badge)
    assert 'id="nav-link-catalog"' in content
    assert 'data-view="catalog"' in content

    # Routing Profiles item is functional (not disabled, no 'Soon' badge)
    assert 'id="nav-link-profiles"' in content
    assert 'data-view="profiles"' in content

    # Diagnostics item is functional (not disabled, no 'Soon' badge)
    assert 'id="nav-link-diagnostics"' in content
    assert 'data-view="diagnostics"' in content

    # Remaining future milestone navigation item (Settings) remains disabled with Soon badge
    assert "Settings" in content
    assert 'aria-disabled="true"' in content
    assert "Soon" in content


def test_catalog_view_dom_elements_present(client: TestClient):
    """Catalog view container and its sub-components exist in HTML shell."""
    response = client.get("/dashboard")
    assert response.status_code == status.HTTP_200_OK
    content = response.text

    # Dedicated view panel
    assert 'id="catalog-view"' in content
    assert "Model Catalog" in content

    # Controls & state containers
    assert 'id="refresh-catalog-btn"' in content
    assert 'id="refresh-catalog-icon"' in content
    assert 'id="catalog-provider-filter"' in content
    assert 'id="catalog-cards-container"' in content
    assert 'id="catalog-empty-state"' in content
    assert 'id="catalog-refresh-alert"' in content
    assert 'id="catalog-error-alert"' in content


def test_providers_view_dom_elements_present(client: TestClient):
    """Providers view container and its sub-components exist in HTML shell."""
    response = client.get("/dashboard")
    assert response.status_code == status.HTTP_200_OK
    content = response.text

    # Dedicated view panel
    assert 'id="providers-view"' in content
    assert "Provider Management" in content

    # Controls & state containers
    assert 'id="refresh-providers-btn"' in content
    assert 'id="providers-cards-container"' in content
    assert 'id="providers-empty-state"' in content
    assert 'id="providers-error-alert"' in content


def test_application_shell_top_header_and_controls(client: TestClient):
    """Top header contains title, status pill, refresh button, and connect trigger."""
    response = client.get("/dashboard")
    assert response.status_code == status.HTTP_200_OK
    content = response.text

    assert 'id="page-title"' in content
    assert 'id="gateway-status-pill"' in content
    assert 'id="gateway-status-label"' in content
    assert 'id="refresh-btn"' in content
    assert 'id="auth-toggle-btn"' in content
    assert 'id="last-updated-text"' in content


def test_application_shell_metric_cards_and_tables(client: TestClient):
    """Overview view contains metric card and table containers."""
    response = client.get("/dashboard")
    assert response.status_code == status.HTTP_200_OK
    content = response.text

    assert 'id="card-gateway-value"' in content
    assert 'id="card-db-value"' in content
    assert 'id="card-providers-value"' in content
    assert 'id="card-catalog-value"' in content
    assert 'id="card-profiles-value"' in content
    assert 'id="providers-table"' in content
    assert 'id="degraded-banner"' in content


# ============================================================================
# 3. Security, DOM Integrity & Safe Probing Tests
# ============================================================================


def test_zero_secret_leakage_in_dashboard_assets(client: TestClient, monkeypatch):
    """Neither HTML nor static JS/CSS contain configured API tokens or credentials."""
    test_secret = "super-secret-production-token-998877"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", test_secret)

    html_res = client.get("/dashboard")
    css_res = client.get("/dashboard/static/dashboard.css")
    js_res = client.get("/dashboard/static/dashboard.js")

    assert test_secret not in html_res.text
    assert test_secret not in css_res.text
    assert test_secret not in js_res.text

    if settings.api_token:
        assert settings.api_token not in html_res.text
        assert settings.api_token not in css_res.text
        assert settings.api_token not in js_res.text

    # Ensure localStorage and sessionStorage are NOT used for credential persistence
    assert "localStorage" not in js_res.text
    assert "sessionStorage" not in js_res.text


def test_dashboard_js_safe_dom_manipulation(client: TestClient):
    """JavaScript controller uses safe DOM creation rather than unsafe innerHTML with variables."""
    js_res = client.get("/dashboard/static/dashboard.js")
    js_text = js_res.text

    # Verify duplicate test prevention mechanism exists
    assert "activeProbes" in js_text
    assert "activeProbes.has" in js_text
    assert "activeProbes.add" in js_text
    assert "activeProbes.delete" in js_text

    # Verify that testProviderConnection calls the explicit POST endpoint
    assert "/api/providers/" in js_text
    assert "/test" in js_text

    # Verify that in-memory map stores probe results per-provider
    assert "providerProbeResults" in js_text

    # Verify catalog refresh in-flight guard and safe DOM manipulation
    assert "isRefreshingCatalog" in js_text
    assert "/api/catalog/refresh" in js_text
    assert "/api/catalog" in js_text
    assert "fetchCatalogData" in js_text
    assert "renderCatalogCards" in js_text
    assert "is_stale" in js_text
    assert "stale-badge" in js_text

    # Verify routing profiles and diagnostics DOM controllers
    assert "fetchProfilesData" in js_text
    assert "renderProfilesCards" in js_text
    assert "isFetchingProfiles" in js_text
    assert "/api/profiles" in js_text
    assert "fetchDiagnosticsData" in js_text
    assert "renderDiagnostics" in js_text
    assert "isFetchingDiagnostics" in js_text
    assert "/api/diagnostics" in js_text


def test_management_api_auth_remains_strictly_enforced(client: TestClient):
    """Direct unauthenticated calls to /api endpoints still return 401."""
    res_diag = client.get("/api/diagnostics")
    assert res_diag.status_code == status.HTTP_401_UNAUTHORIZED

    res_prov = client.get("/api/providers")
    assert res_prov.status_code == status.HTTP_401_UNAUTHORIZED

    res_test = client.post("/api/providers/ollama/test")
    assert res_test.status_code == status.HTTP_401_UNAUTHORIZED

    res_cat = client.get("/api/catalog")
    assert res_cat.status_code == status.HTTP_401_UNAUTHORIZED

    res_ref = client.post("/api/catalog/refresh")
    assert res_ref.status_code == status.HTTP_401_UNAUTHORIZED

    res_prof = client.get("/api/profiles")
    assert res_prof.status_code == status.HTTP_401_UNAUTHORIZED


def test_existing_health_and_api_routes_unaffected(client: TestClient):
    """Existing endpoints (/health, /v1/models) continue to function identically."""
    health_res = client.get("/health")
    assert health_res.status_code == status.HTTP_200_OK
    assert health_res.json()["status"] == "ok"

    v1_models_res = client.get("/v1/models")
    assert v1_models_res.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# 4. Provider Connection Probe Integration Contract Tests
# ============================================================================


def test_provider_test_connection_healthy_contract(monkeypatch):
    """POST /api/providers/{id}/test returns healthy probe result with latency."""
    token = "test-provider-probe-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings
    from backend.providers.registry import ProviderRegistry

    main_module.settings = Settings()
    mock_adapter = ControllableMockAdapter("test_healthy", healthy=True, latency_ms=18.4)

    test_reg = ProviderRegistry()
    test_reg.register(mock_adapter)
    app.state.registry = test_reg

    with TestClient(app) as test_client:
        headers = {"Authorization": f"Bearer {token}"}
        res = test_client.post("/api/providers/test_healthy/test", headers=headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["provider_id"] == "test_healthy"
        assert data["status"] == "healthy"
        assert data["latency_ms"] == 18.4
        assert data["error"] is None
        assert mock_adapter.probe_call_count == 1


def test_provider_test_connection_unhealthy_contract(monkeypatch):
    """POST /api/providers/{id}/test returns unhealthy probe result with sanitized error."""
    token = "test-provider-probe-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings
    from backend.providers.registry import ProviderRegistry

    main_module.settings = Settings()
    mock_adapter = ControllableMockAdapter(
        "test_unhealthy",
        healthy=False,
        latency_ms=45.0,
        msg="Connection timeout to [PATH]",
    )

    test_reg = ProviderRegistry()
    test_reg.register(mock_adapter)
    app.state.registry = test_reg

    with TestClient(app) as test_client:
        headers = {"Authorization": f"Bearer {token}"}
        res = test_client.post("/api/providers/test_unhealthy/test", headers=headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["provider_id"] == "test_unhealthy"
        assert data["status"] == "unhealthy"
        assert data["latency_ms"] == 45.0
        assert "Connection timeout" in data["error"]
        assert mock_adapter.probe_call_count == 1


def test_provider_list_does_not_implicitly_probe(monkeypatch):
    """GET /api/providers never runs connection probes automatically."""
    token = "test-provider-probe-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings
    from backend.providers.registry import ProviderRegistry

    main_module.settings = Settings()
    mock_adapter = ControllableMockAdapter("no_probe", healthy=True)

    test_reg = ProviderRegistry()
    test_reg.register(mock_adapter)
    app.state.registry = test_reg

    with TestClient(app) as test_client:
        headers = {"Authorization": f"Bearer {token}"}
        res = test_client.get("/api/providers", headers=headers)
        assert res.status_code == status.HTTP_200_OK
        # Zero probe calls were made on list
        assert mock_adapter.probe_call_count == 0


def test_provider_test_unknown_provider_returns_404(monkeypatch):
    """POST /api/providers/{id}/test returns 404 for unknown provider."""
    token = "test-provider-probe-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings

    main_module.settings = Settings()

    with TestClient(app) as test_client:
        headers = {"Authorization": f"Bearer {token}"}
        res = test_client.post("/api/providers/non_existent/test", headers=headers)
        assert res.status_code == status.HTTP_404_NOT_FOUND
        assert "not registered" in res.json()["error"]["message"]


# ============================================================================
# 4. Model Catalog Explorer & On-Demand Discovery Tests (P7-M4)
# ============================================================================


def test_catalog_list_and_card_rendering_contract(monkeypatch):
    """GET /api/catalog returns active, stale, and colon-tagged model metadata."""
    token = "test-catalog-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings
    from backend.providers.registry import ProviderRegistry

    main_module.settings = Settings()
    test_reg = ProviderRegistry()
    test_cat = ModelCatalog(registry=test_reg)

    # 1. Active local model with colon in raw model ID
    entry1 = CatalogEntry(
        composite_id="ollama:llama3.2:latest",
        provider_id="ollama",
        model_id="llama3.2:latest",
        display_name="Llama 3.2 Latest",
        capabilities=ModelCapability(
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
            context_window=128000,
        ),
        is_local=True,
        is_stale=False,
        last_seen_at=1700000000.0,
    )
    # 2. Stale hosted model
    entry2 = CatalogEntry(
        composite_id="mock:gpt-4o:preview",
        provider_id="mock",
        model_id="gpt-4o:preview",
        display_name="GPT-4o Preview",
        capabilities=ModelCapability(
            supports_streaming=True,
            supports_tools=False,
            supports_vision=True,
            context_window=None,
        ),
        is_local=False,
        is_stale=True,
        last_seen_at=1690000000.0,
    )
    # 3. Another local model
    entry3 = CatalogEntry(
        composite_id="ollama:deepseek-r1:14b",
        provider_id="ollama",
        model_id="deepseek-r1:14b",
        display_name="DeepSeek R1 14B",
        capabilities=ModelCapability(
            supports_streaming=True,
            supports_tools=False,
            supports_vision=False,
            context_window=64000,
        ),
        is_local=True,
        is_stale=False,
        last_seen_at=1700000050.0,
    )

    test_cat._entries = {
        entry1.composite_id: entry1,
        entry2.composite_id: entry2,
        entry3.composite_id: entry3,
    }

    app.state.registry = test_reg
    app.state.catalog = test_cat

    with TestClient(app) as test_client:
        headers = {"Authorization": f"Bearer {token}"}
        res = test_client.get("/api/catalog", headers=headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()["data"]
        assert len(data) == 3

        # Verify entry1 active local model
        item1 = next(m for m in data if m["composite_id"] == "ollama:llama3.2:latest")
        assert item1["provider_id"] == "ollama"
        assert item1["model_id"] == "llama3.2:latest"
        assert item1["display_name"] == "Llama 3.2 Latest"
        assert item1["is_local"] is True
        assert item1["is_stale"] is False
        assert item1["capabilities"]["supports_streaming"] is True
        assert item1["capabilities"]["supports_tools"] is True
        assert item1["capabilities"]["supports_vision"] is False
        assert item1["capabilities"]["context_window"] == 128000

        # Verify entry2 stale hosted model
        item2 = next(m for m in data if m["composite_id"] == "mock:gpt-4o:preview")
        assert item2["provider_id"] == "mock"
        assert item2["is_local"] is False
        assert item2["is_stale"] is True
        assert item2["capabilities"]["supports_vision"] is True
        assert item2["capabilities"]["context_window"] is None

        # Verify provider filtering via query parameter
        filtered_res = test_client.get("/api/catalog?provider_id=ollama", headers=headers)
        assert filtered_res.status_code == status.HTTP_200_OK
        filtered_data = filtered_res.json()["data"]
        assert len(filtered_data) == 2
        assert all(m["provider_id"] == "ollama" for m in filtered_data)


def test_catalog_list_does_not_implicitly_refresh(monkeypatch):
    """GET /api/catalog only reads cached entries and never triggers discovery."""
    token = "test-catalog-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings
    from backend.providers.registry import ProviderRegistry

    main_module.settings = Settings()
    mock_adapter = ControllableMockAdapter("passive_provider", healthy=True)
    test_reg = ProviderRegistry()
    test_reg.register(mock_adapter)
    test_cat = ModelCatalog(registry=test_reg)

    app.state.registry = test_reg
    app.state.catalog = test_cat

    with TestClient(app) as test_client:
        headers = {"Authorization": f"Bearer {token}"}
        res = test_client.get("/api/catalog", headers=headers)
        assert res.status_code == status.HTTP_200_OK
        # Must NOT call adapter list_models or test_connection
        assert mock_adapter.discovery_call_count == 0
        assert mock_adapter.probe_call_count == 0


def test_catalog_refresh_success_contract(monkeypatch):
    """POST /api/catalog/refresh executes discovery across providers and reports results."""
    token = "test-catalog-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings
    from backend.providers.registry import ProviderRegistry

    main_module.settings = Settings()
    mock_model1 = ProviderModel(
        id="test-model:v1",
        provider_id="prov1",
        display_name="Test Model V1",
        capabilities=ModelCapability(supports_streaming=True, context_window=32000),
    )
    mock_model2 = ProviderModel(
        id="test-model:v2",
        provider_id="prov2",
        display_name="Test Model V2",
        capabilities=ModelCapability(supports_streaming=True, context_window=16000),
    )
    adapter1 = ControllableMockAdapter("prov1", models=[mock_model1])
    adapter2 = ControllableMockAdapter("prov2", models=[mock_model2])

    test_reg = ProviderRegistry()
    test_reg.register(adapter1)
    test_reg.register(adapter2)
    test_cat = ModelCatalog(registry=test_reg)

    app.state.registry = test_reg
    app.state.catalog = test_cat

    with TestClient(app) as test_client:
        headers = {"Authorization": f"Bearer {token}"}
        res = test_client.post("/api/catalog/refresh", headers=headers, json={})
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["total_refreshed"] == 2
        assert data["successful_refreshes"] == 2
        assert data["failed_refreshes"] == 0
        assert len(data["results"]) == 2

        assert adapter1.discovery_call_count == 1
        assert adapter2.discovery_call_count == 1

        # Check refreshed models exist in catalog
        cat_res = test_client.get("/api/catalog", headers=headers)
        assert cat_res.status_code == status.HTTP_200_OK
        cat_data = cat_res.json()["data"]
        assert len(cat_data) == 2


def test_catalog_refresh_partial_failure_contract(monkeypatch):
    """POST /api/catalog/refresh reports partial discovery when a provider fails."""
    token = "test-catalog-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings
    from backend.providers.registry import ProviderRegistry

    main_module.settings = Settings()
    mock_model = ProviderModel(
        id="working-model",
        provider_id="healthy_p",
        display_name="Working Model",
        capabilities=ModelCapability(supports_streaming=True),
    )
    healthy_adapter = ControllableMockAdapter("healthy_p", models=[mock_model])
    failing_adapter = ControllableMockAdapter("failing_p", fail_discovery=True)

    test_reg = ProviderRegistry()
    test_reg.register(healthy_adapter)
    test_reg.register(failing_adapter)
    test_cat = ModelCatalog(registry=test_reg)

    app.state.registry = test_reg
    app.state.catalog = test_cat

    with TestClient(app) as test_client:
        headers = {"Authorization": f"Bearer {token}"}
        res = test_client.post("/api/catalog/refresh", headers=headers, json={})
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["total_refreshed"] == 2
        assert data["successful_refreshes"] == 1
        assert data["failed_refreshes"] == 1

        failed_entry = next(r for r in data["results"] if r["provider_id"] == "failing_p")
        assert failed_entry["success"] is False
        assert "Connection failed" in failed_entry["error"]
        assert "[PATH]" in failed_entry["error"]  # Sanitized path


def test_catalog_refresh_single_provider_filter(monkeypatch):
    """POST /api/catalog/refresh with provider_id refreshes only that provider."""
    token = "test-catalog-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings
    from backend.providers.registry import ProviderRegistry

    main_module.settings = Settings()
    adapter1 = ControllableMockAdapter("p_single_1")
    adapter2 = ControllableMockAdapter("p_single_2")

    test_reg = ProviderRegistry()
    test_reg.register(adapter1)
    test_reg.register(adapter2)
    test_cat = ModelCatalog(registry=test_reg)

    app.state.registry = test_reg
    app.state.catalog = test_cat

    with TestClient(app) as test_client:
        headers = {"Authorization": f"Bearer {token}"}
        res = test_client.post(
            "/api/catalog/refresh",
            headers=headers,
            json={"provider_id": "p_single_1"},
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["total_refreshed"] == 1
        assert data["successful_refreshes"] == 1
        assert data["results"][0]["provider_id"] == "p_single_1"
        assert adapter1.discovery_call_count == 1
        assert adapter2.discovery_call_count == 0


def test_catalog_refresh_unknown_provider_returns_404(monkeypatch):
    """POST /api/catalog/refresh with unknown provider returns 404."""
    token = "test-catalog-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings

    main_module.settings = Settings()

    with TestClient(app) as test_client:
        headers = {"Authorization": f"Bearer {token}"}
        res = test_client.post(
            "/api/catalog/refresh",
            headers=headers,
            json={"provider_id": "ghost_provider"},
        )
        assert res.status_code == status.HTTP_404_NOT_FOUND
        assert "not registered" in res.json()["error"]["message"]


# ============================================================================
# 5. Routing Profile Explorer & Diagnostics Inspector Tests (P7-M5)
# ============================================================================


def test_profiles_view_dom_elements_present(client: TestClient):
    """Routing Profiles view container and its sub-components exist in HTML shell."""
    response = client.get("/dashboard")
    assert response.status_code == status.HTTP_200_OK
    content = response.text

    # Dedicated view panel
    assert 'id="profiles-view"' in content
    assert "Routing Profiles" in content

    # Controls & state containers
    assert 'id="refresh-profiles-btn"' in content
    assert 'id="profiles-cards-container"' in content
    assert 'id="profiles-empty-state"' in content
    assert 'id="profiles-error-alert"' in content


def test_diagnostics_view_dom_elements_present(client: TestClient):
    """Diagnostics Inspector view container and its sub-components exist in HTML shell."""
    response = client.get("/dashboard")
    assert response.status_code == status.HTTP_200_OK
    content = response.text

    # Dedicated view panel
    assert 'id="diagnostics-view"' in content
    assert "Diagnostics Inspector" in content

    # Controls & state containers
    assert 'id="refresh-diagnostics-btn"' in content
    assert 'id="diagnostics-content-container"' in content
    assert 'id="diagnostics-error-alert"' in content
    assert 'id="diagnostics-degraded-alert"' in content


def test_profiles_list_and_card_rendering_contract(monkeypatch):
    """GET /api/profiles returns candidate ordering, retry budget, and capability constraints."""
    token = "test-profiles-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings

    main_module.settings = Settings()
    test_engine = RoutingEngine()

    # Custom profile with candidate priority sequence
    custom_profile = RoutingProfile(
        name="custom_eval",
        description="Evaluation profile with strict candidate failover",
        candidates=["ollama:llama3.2:latest", "mock:eval-fallback"],
        max_retries=3,
        timeout_seconds=45.0,
        required_capabilities=ModelCapability(
            supports_streaming=True,
            supports_tools=True,
            context_window=64000,
        ),
    )
    test_engine.register_profile(custom_profile)
    app.state.routing_engine = test_engine

    with TestClient(app) as test_client:
        headers = {"Authorization": f"Bearer {token}"}
        res = test_client.get("/api/profiles", headers=headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()["data"]

        # Ensure built-ins + custom exist
        names = [p["name"] for p in data]
        assert "default" in names
        assert "coding" in names
        assert "custom_eval" in names

        custom_item = next(p for p in data if p["name"] == "custom_eval")
        assert custom_item["name"] == "custom_eval"
        assert custom_item["description"] == "Evaluation profile with strict candidate failover"
        # Candidate sequence priority check
        assert custom_item["candidates"] == ["ollama:llama3.2:latest", "mock:eval-fallback"]
        assert custom_item["max_retries"] == 3
        assert custom_item["timeout_seconds"] == 45.0
        assert custom_item["required_capabilities"]["supports_streaming"] is True
        assert custom_item["required_capabilities"]["supports_tools"] is True
        assert custom_item["required_capabilities"]["context_window"] == 64000


def test_diagnostics_inspector_normal_and_degraded_contracts(monkeypatch):
    """GET /api/diagnostics returns sanitized runtime, persistence, and inventory metrics."""
    token = "test-diagnostics-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings

    main_module.settings = Settings()

    with TestClient(app) as test_client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Normal mode check
        res_normal = test_client.get("/api/diagnostics", headers=headers)
        assert res_normal.status_code == status.HTTP_200_OK
        data_normal = res_normal.json()
        assert data_normal["status"] == "ok"
        assert data_normal["database"]["available"] is True
        assert data_normal["database"]["degraded"] is False
        assert data_normal["database"]["mode"] in ("wal", "memory")
        assert data_normal["database"]["reason"] is None
        assert isinstance(data_normal["registered_providers_count"], int)
        assert isinstance(data_normal["catalog_entries_count"], int)
        assert isinstance(data_normal["stale_models_count"], int)
        assert isinstance(data_normal["routing_profiles_count"], int)

        # 2. Degraded mode with secret/path sanitization
        db_mgr = app.state.db_manager
        db_mgr.is_degraded = True
        db_mgr.degraded_reason = (
            "IOError writing to C:\\FreeFlow\\secret_store.db with token=secret123"
        )

        res_degraded = test_client.get("/api/diagnostics", headers=headers)
        assert res_degraded.status_code == status.HTTP_200_OK
        data_degraded = res_degraded.json()
        assert data_degraded["database"]["degraded"] is True
        assert data_degraded["database"]["mode"] == "in_memory_fallback"
        # Assert path and secrets are scrubbed
        sanitized_reason = data_degraded["database"]["reason"]
        assert "secret123" not in sanitized_reason
        assert "C:\\FreeFlow" not in sanitized_reason
        assert "[PATH]" in sanitized_reason
        assert "[REDACTED]" in sanitized_reason


def test_diagnostics_inspector_unavailable_database_contract(monkeypatch):
    """GET /api/diagnostics accurately reflects uninitialized/unavailable database."""
    token = "test-diagnostics-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings

    main_module.settings = Settings()

    with TestClient(app) as test_client:
        app.state.db_manager = None
        headers = {"Authorization": f"Bearer {token}"}
        res = test_client.get("/api/diagnostics", headers=headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["database"]["available"] is False
        assert data["database"]["degraded"] is True
        assert data["database"]["mode"] == "none"
        assert "DatabaseManager not initialized" in data["database"]["reason"]


def test_profiles_and_diagnostics_do_not_implicitly_probe_or_refresh(monkeypatch):
    """GET /api/profiles and /api/diagnostics never run reachability probes or discovery."""
    token = "test-inspect-token"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", token)

    import backend.main as main_module
    from backend.config import Settings
    from backend.providers.registry import ProviderRegistry

    main_module.settings = Settings()
    mock_adapter = ControllableMockAdapter("passive_inspector", healthy=True)
    test_reg = ProviderRegistry()
    test_reg.register(mock_adapter)
    test_cat = ModelCatalog(registry=test_reg)
    test_engine = RoutingEngine()

    app.state.registry = test_reg
    app.state.catalog = test_cat
    app.state.routing_engine = test_engine

    with TestClient(app) as test_client:
        headers = {"Authorization": f"Bearer {token}"}

        res_prof = test_client.get("/api/profiles", headers=headers)
        assert res_prof.status_code == status.HTTP_200_OK

        res_diag = test_client.get("/api/diagnostics", headers=headers)
        assert res_diag.status_code == status.HTTP_200_OK

        # Ensure no discovery or probes were triggered
        assert mock_adapter.discovery_call_count == 0
        assert mock_adapter.probe_call_count == 0
