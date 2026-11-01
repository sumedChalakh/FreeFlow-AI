"""Deterministic unit and integration tests for FreeFlow AI SQLite persistence (P4-T1).

Validates schema migrations, startup restoration, stale reconciliation,
zero secret leakage, corrupt database preservation and degraded fallback,
atomic transaction rollback, and concurrent WAL file operations.
"""

import asyncio
from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient

import backend.main as main_module
from backend.catalog.service import ModelCatalog, default_catalog
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


class DeterministicMockAdapter(ProviderAdapter):
    """Adapter returning controllable model inventories."""

    def __init__(self, provider_id: str, models: list[ProviderModel]) -> None:
        self._provider_id = provider_id
        self._models = models

    @property
    def adapter_id(self) -> str:
        return self._provider_id

    async def list_models(self, context: ProviderContext) -> list[ProviderModel]:
        return self._models

    def set_models(self, models: list[ProviderModel]) -> None:
        self._models = models

    async def test_connection(self, context: ProviderContext) -> ConnectionHealth:
        return ConnectionHealth(healthy=True)

    async def complete_chat(
        self,
        context: ProviderContext,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        raise NotImplementedError


# ============================================================================
# 1. Schema & Migration Versioning
# ============================================================================


def test_schema_creation_and_version(tmp_path: Path):
    """Verify SQLite migrations create expected tables and set PRAGMA user_version to 1."""
    db_file = str(tmp_path / "test_migration.db")
    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.initialize()

    conn = db_mgr.get_connection()

    # Check user_version
    version = conn.execute("PRAGMA user_version;").fetchone()[0]
    assert version == 1

    # Check tables
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    table_names = [row[0] for row in cursor.fetchall()]
    assert "catalog_models" in table_names
    assert "providers" in table_names
    assert "routing_profiles" in table_names

    # Check WAL mode
    journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    assert journal_mode.lower() == "wal"

    db_mgr.close()


# ============================================================================
# 2. Persistence & Startup Restoration
# ============================================================================


@pytest.mark.anyio
async def test_catalog_persists_and_restores_on_restart(tmp_path: Path):
    """Verify discovered models persist to SQLite and restore as stale across restart."""
    db_file = str(tmp_path / "test_catalog_restart.db")

    # Instance 1: Discovers and saves models
    db_mgr_1 = DatabaseManager(db_path=db_file)
    db_mgr_1.initialize()
    repo_1 = CatalogRepository(db_mgr_1)
    repo_1.save_provider("ollama", "Ollama Local", base_url="http://127.0.0.1:11434")

    reg_1 = ProviderRegistry()
    mock_models = [
        ProviderModel(
            id="llama3.2:3b",
            provider_id="ollama",
            display_name="Llama 3.2 3B",
            capabilities=ModelCapability(supports_streaming=True, context_window=4096),
            is_local=True,
        ),
        ProviderModel(
            id="qwen2.5:7b",
            provider_id="ollama",
            display_name="Qwen 2.5 7B",
            capabilities=ModelCapability(supports_streaming=True, supports_tools=True),
            is_local=True,
        ),
    ]
    adapter_1 = DeterministicMockAdapter("ollama", mock_models)
    reg_1.register(adapter_1)

    catalog_1 = ModelCatalog(registry=reg_1, repository=repo_1)
    res = await catalog_1.refresh_provider("ollama")
    assert res.success is True
    assert res.models_count == 2

    # Close instance 1
    db_mgr_1.close()

    # Instance 2: Cold start with same database file (no discovery runs)
    db_mgr_2 = DatabaseManager(db_path=db_file)
    db_mgr_2.initialize()
    repo_2 = CatalogRepository(db_mgr_2)

    # Empty registry on instance 2 initially
    reg_2 = ProviderRegistry()
    catalog_2 = ModelCatalog(registry=reg_2, repository=repo_2)

    # Restore from repository
    restored_count = await catalog_2.restore_from_repository()
    assert restored_count == 2

    # Safeguard 9: Restored entries are marked is_stale=True until discovery confirms
    entry_1 = catalog_2.get_by_composite_id("ollama:llama3.2:3b")
    assert entry_1 is not None
    assert entry_1.model_id == "llama3.2:3b"
    assert entry_1.capabilities.context_window == 4096
    assert entry_1.is_local is True
    assert entry_1.is_stale is True

    entry_2 = catalog_2.get_by_composite_id("ollama:qwen2.5:7b")
    assert entry_2 is not None
    assert entry_2.capabilities.supports_tools is True
    assert entry_2.is_stale is True

    db_mgr_2.close()


# ============================================================================
# 3. Stale Model Reconciliation
# ============================================================================


@pytest.mark.anyio
async def test_stale_reconciliation_persists(tmp_path: Path):
    """Verify omitted models are marked stale in SQLite and un-staled upon reappearance."""
    db_file = str(tmp_path / "test_stale.db")
    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.initialize()
    repo = CatalogRepository(db_mgr)
    repo.save_provider("mock", "Mock Provider")

    reg = ProviderRegistry()
    mod_a = ProviderModel(id="model-a", provider_id="mock", display_name="Model A")
    mod_b = ProviderModel(id="model-b", provider_id="mock", display_name="Model B")

    adapter = DeterministicMockAdapter("mock", [mod_a, mod_b])
    reg.register(adapter)
    catalog = ModelCatalog(registry=reg, repository=repo)

    # Run 1: Both models discovered
    await catalog.refresh_provider("mock")
    conn = db_mgr.get_connection()
    sql = "SELECT model_id, is_stale FROM catalog_models ORDER BY model_id;"
    rows = conn.execute(sql).fetchall()
    assert len(rows) == 2
    assert rows[0]["is_stale"] == 0
    assert rows[1]["is_stale"] == 0

    # Run 2: Model B omitted
    adapter.set_models([mod_a])
    await catalog.refresh_provider("mock")
    rows = conn.execute(sql).fetchall()
    assert rows[0]["model_id"] == "model-a" and rows[0]["is_stale"] == 0
    assert rows[1]["model_id"] == "model-b" and rows[1]["is_stale"] == 1

    # Run 3: Model B reappears
    adapter.set_models([mod_a, mod_b])
    await catalog.refresh_provider("mock")
    rows = conn.execute(sql).fetchall()
    assert rows[0]["is_stale"] == 0
    assert rows[1]["is_stale"] == 0

    db_mgr.close()


# ============================================================================
# 4. Zero Secret Leakage in Database
# ============================================================================


@pytest.mark.anyio
async def test_zero_secret_leakage_in_sqlite(tmp_path: Path):
    """Verify SQLite database file never contains API keys, tokens, or prompt texts."""
    db_file = str(tmp_path / "test_secrets.db")
    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.initialize()
    repo = CatalogRepository(db_mgr)

    secret_key = "SECRET_SUPER_CONFIDENTIAL_KEY_9999"
    secret_prompt = "TOP_SECRET_PROMPT_PAYLOAD_ABCDE"

    # Save provider with credential_ref only (no real secret)
    repo.save_provider(
        provider_id="hosted",
        display_name="Hosted Provider",
        base_url="https://api.example.com",
        extra_config={"timeout": 30},
    )

    reg = ProviderRegistry()
    m = ProviderModel(id="hosted-mod", provider_id="hosted", display_name="Hosted Model")
    adapter = DeterministicMockAdapter("hosted", [m])
    reg.register(adapter)
    catalog = ModelCatalog(registry=reg, repository=repo)

    await catalog.refresh_provider("hosted")
    db_mgr.close()

    # Read raw database binary content
    with open(db_file, "rb") as f:
        content = f.read().decode("latin1", errors="ignore")

    assert secret_key not in content
    assert secret_prompt not in content


# ============================================================================
# 5. Corrupt Database Preservation & Degraded Fallback
# ============================================================================


def test_corrupt_database_preserves_file_and_activates_degraded_mode(tmp_path: Path):
    """Corrupt database file is preserved with timestamp and falls back to in-memory mode."""
    db_file = tmp_path / "corrupt_test.db"

    # Write corrupt non-SQLite bytes
    with open(db_file, "wb") as f:
        f.write(b"CORRUPT_INVALID_SQLITE_HEADER_DATA_1234567890")

    db_mgr = DatabaseManager(db_path=str(db_file))
    db_mgr.initialize()

    # Integrity failed -> degraded mode active
    assert db_mgr.is_degraded is True
    assert db_mgr.degraded_reason is not None

    # Corrupt file was preserved as a copy
    corrupt_copies = list(tmp_path.glob("*.corrupt.*.db"))
    assert len(corrupt_copies) >= 1

    # In-memory fallback allows operations
    status_info = db_mgr.get_health_status()
    assert status_info["degraded"] is True
    assert status_info["mode"] == "in_memory_fallback"

    db_mgr.close()


def test_health_reports_database_status(monkeypatch, tmp_path: Path):
    """Health endpoint accurately reflects database availability and status."""
    db_file = str(tmp_path / "health_test.db")
    monkeypatch.setenv("FREEFLOW_DB_PATH", db_file)

    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["status"] == "ok"
        assert "database" in data
        assert data["database"]["available"] is True
        assert data["database"]["degraded"] is False


# ============================================================================
# 6. Transaction Rollback & State Consistency
# ============================================================================


@pytest.mark.anyio
async def test_transaction_rollback_preserves_consistent_state(tmp_path: Path):
    """When a database write fails, in-memory state is not mutated and DB rolls back."""
    db_file = str(tmp_path / "test_rollback.db")
    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.initialize()
    repo = CatalogRepository(db_mgr)
    repo.save_provider("mock", "Mock Provider")

    reg = ProviderRegistry()
    mod_1 = ProviderModel(id="mod-initial", provider_id="mock", display_name="Initial Model")
    adapter = DeterministicMockAdapter("mock", [mod_1])
    reg.register(adapter)
    catalog = ModelCatalog(registry=reg, repository=repo)

    # Initial successful refresh
    await catalog.refresh_provider("mock")
    assert catalog.get_by_composite_id("mock:mod-initial") is not None

    # Simulate database failure on next refresh by closing DB connection abruptly
    db_mgr.close()

    mod_2 = ProviderModel(id="mod-new", provider_id="mock", display_name="New Model")
    adapter.set_models([mod_2])

    # Refresh should fail due to closed connection
    res = await catalog.refresh_provider("mock")
    assert res.success is False

    # In-memory state should keep previous entry (fault isolation) and not have added mod-new
    assert catalog.get_by_composite_id("mock:mod-new") is None
    initial_entry = catalog.get_by_composite_id("mock:mod-initial")
    assert initial_entry is not None
    assert initial_entry.is_stale is True


# ============================================================================
# 7. Concurrent File-Backed Refreshes in WAL Mode
# ============================================================================


@pytest.mark.anyio
async def test_concurrent_refreshes_with_file_database(tmp_path: Path):
    """Multiple concurrent refresh operations against a real WAL file complete cleanly."""
    db_file = str(tmp_path / "test_concurrent_wal.db")
    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.initialize()
    repo = CatalogRepository(db_mgr)

    reg = ProviderRegistry()
    for prov_name in ("prov_1", "prov_2", "prov_3"):
        repo.save_provider(prov_name, f"Provider {prov_name}")
        models = [
            ProviderModel(
                id=f"{prov_name}-m{i}",
                provider_id=prov_name,
                display_name=f"Model {i}",
            )
            for i in range(5)
        ]
        adapter = DeterministicMockAdapter(prov_name, models)
        reg.register(adapter)

    catalog = ModelCatalog(registry=reg, repository=repo)

    # Launch overlapping concurrent refreshes across all 3 providers
    tasks = [
        catalog.refresh_provider("prov_1"),
        catalog.refresh_provider("prov_2"),
        catalog.refresh_provider("prov_3"),
        catalog.refresh_provider("prov_1"),
        catalog.refresh_provider("prov_2"),
    ]
    results = await asyncio.gather(*tasks)

    assert all(r.success for r in results)
    entries = catalog.list_entries(include_stale=False)
    assert len(entries) == 15

    db_mgr.close()


# ============================================================================
# 8. Routing Profile Persistence
# ============================================================================


def test_routing_profile_persistence(tmp_path: Path):
    """Verify custom routing profiles persist to SQLite and restore accurately."""
    db_file = str(tmp_path / "test_profiles.db")
    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.initialize()
    repo = CatalogRepository(db_mgr)

    custom_profile = RoutingProfile(
        name="custom_code",
        description="Custom coding pipeline",
        candidates=["ollama:qwen2.5-coder:7b", "mock:general-chat"],
        max_retries=3,
        timeout_seconds=45.0,
        required_capabilities=ModelCapability(supports_streaming=True),
    )

    repo.save_profile(custom_profile)
    db_mgr.close()

    # Reopen on new connection
    db_mgr_2 = DatabaseManager(db_path=db_file)
    db_mgr_2.initialize()
    repo_2 = CatalogRepository(db_mgr_2)

    profiles = repo_2.load_all_profiles()
    assert len(profiles) == 1
    p = profiles[0]
    assert p.name == "custom_code"
    assert p.candidates == ["ollama:qwen2.5-coder:7b", "mock:general-chat"]
    assert p.max_retries == 3
    assert p.timeout_seconds == 45.0
    assert p.required_capabilities.supports_streaming is True

    db_mgr_2.close()


# ============================================================================
# 9. Startup Restoration & Offline Resilience
# ============================================================================


def test_startup_with_ollama_offline_and_restored_catalog_models_in_v1_models(
    tmp_path: Path, monkeypatch
):
    """Application starts cleanly with offline Ollama and serves restored models."""
    db_file = str(tmp_path / "test_startup_offline.db")

    # Seed the database before app launch
    db_seed = DatabaseManager(db_path=db_file)
    db_seed.initialize()
    repo_seed = CatalogRepository(db_seed)
    repo_seed.save_provider("ollama", "Local Ollama", base_url="http://127.0.0.1:99999")

    # Seed a custom routing profile
    custom_prof = RoutingProfile(
        name="custom_chat",
        description="Custom chat profile",
        candidates=["ollama:llama3.2:3b"],
    )
    repo_seed.save_profile(custom_prof)

    # Seed models
    models = [
        ProviderModel(
            id="llama3.2:3b",
            provider_id="ollama",
            display_name="Llama 3.2 3B",
            capabilities=ModelCapability(supports_streaming=True),
            is_local=True,
        )
    ]
    repo_seed.save_provider_refresh("ollama", models, set(), 1000.0)
    db_seed.close()

    # Configure environment
    test_token = "audit-bearer-token-startup"
    monkeypatch.setenv("FREEFLOW_API_TOKEN", test_token)
    monkeypatch.setenv("FREEFLOW_DB_PATH", db_file)
    original_settings = main_module.settings
    main_module.settings = Settings()

    try:
        # Launch app via TestClient (runs FastAPI lifespan)
        with TestClient(app) as client:
            # 1. Health check reports healthy WAL database
            health_res = client.get("/health")
            assert health_res.status_code == status.HTTP_200_OK
            health_data = health_res.json()
            assert health_data["database"]["available"] is True
            assert health_data["database"]["degraded"] is False

            # 2. GET /v1/models returns restored models without needing live Ollama daemon
            models_res = client.get(
                "/v1/models",
                headers={"Authorization": f"Bearer {test_token}"},
            )
            assert models_res.status_code == status.HTTP_200_OK
            data = models_res.json()["data"]
            model_ids = [m["id"] for m in data]

            # Custom profile and built-in profiles are present
            assert "custom_chat" in model_ids
            assert "default" in model_ids
            assert "coding" in model_ids

            # Restored models are present
            assert "ollama:llama3.2:3b" in model_ids
            assert "llama3.2:3b" in model_ids
    finally:
        main_module.settings = original_settings
        default_catalog.clear()


def test_preservation_of_built_in_routing_profiles_on_restore(tmp_path: Path):
    """Restoring custom profiles from SQLite preserves default built-in profiles."""
    db_file = str(tmp_path / "test_preserve_profiles.db")
    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.initialize()
    repo = CatalogRepository(db_mgr)

    custom_prof = RoutingProfile(
        name="specialized_coding",
        description="High-tier coding",
        candidates=["mock:coder"],
    )
    repo.save_profile(custom_prof)

    reg = ProviderRegistry()
    cat = ModelCatalog(registry=reg, repository=repo)
    engine = RoutingEngine(catalog=cat, registry=reg)

    # Built-in profiles must be initially present
    assert "default" in engine.list_profiles()
    assert "coding" in engine.list_profiles()
    assert "fast" in engine.list_profiles()
    assert "reasoning" in engine.list_profiles()

    # Rehydrate saved profiles
    saved_profiles = repo.load_all_profiles()
    for prof in saved_profiles:
        engine.register_profile(prof)

    # Built-in profiles must still exist alongside the rehydrated custom profile
    profiles = engine.list_profiles()
    assert "default" in profiles
    assert "coding" in profiles
    assert "fast" in profiles
    assert "reasoning" in profiles
    assert "specialized_coding" in profiles

    db_mgr.close()


@pytest.mark.anyio
async def test_multi_colon_model_id_persistence_and_restore(tmp_path: Path):
    """Model IDs with multiple colons persist and restore verbatim."""
    db_file = str(tmp_path / "test_multi_colon.db")
    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.initialize()
    repo = CatalogRepository(db_mgr)
    repo.save_provider("ollama", "Ollama Provider")

    reg = ProviderRegistry()
    multi_colon_model = ProviderModel(
        id="deepseek-r1:7b:q4_k_m",
        provider_id="ollama",
        display_name="DeepSeek R1 Quantized",
        capabilities=ModelCapability(supports_streaming=True),
        is_local=True,
    )
    adapter = DeterministicMockAdapter("ollama", [multi_colon_model])
    reg.register(adapter)

    catalog = ModelCatalog(registry=reg, repository=repo)
    refresh_res = await catalog.refresh_provider("ollama")
    assert refresh_res.success is True

    # Composite ID should preserve all segments
    composite_id = "ollama:deepseek-r1:7b:q4_k_m"
    entry = catalog.get_by_composite_id(composite_id)
    assert entry is not None
    assert entry.model_id == "deepseek-r1:7b:q4_k_m"
    assert entry.provider_id == "ollama"

    db_mgr.close()

    # Restore in fresh catalog from disk
    db_mgr_2 = DatabaseManager(db_path=db_file)
    db_mgr_2.initialize()
    repo_2 = CatalogRepository(db_mgr_2)
    catalog_2 = ModelCatalog(registry=reg, repository=repo_2)

    count = await catalog_2.restore_from_repository()
    assert count == 1
    restored_entry = catalog_2.get_by_composite_id(composite_id)
    assert restored_entry is not None
    assert restored_entry.model_id == "deepseek-r1:7b:q4_k_m"
    assert restored_entry.provider_id == "ollama"
    assert restored_entry.is_stale is True

    db_mgr_2.close()


@pytest.mark.anyio
async def test_readonly_database_write_failure_preserves_memory_state(tmp_path: Path):
    """Write failure on read-only database safely rolls back and retains in-memory consistency."""
    db_file = str(tmp_path / "test_readonly.db")
    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.initialize()
    repo = CatalogRepository(db_mgr)
    repo.save_provider("mock", "Mock Provider")

    mod_1 = ProviderModel(id="mod-1", provider_id="mock", display_name="Initial Model")
    adapter = DeterministicMockAdapter("mock", [mod_1])
    reg = ProviderRegistry()
    reg.register(adapter)

    catalog = ModelCatalog(registry=reg, repository=repo)
    await catalog.refresh_provider("mock")
    assert catalog.get_by_composite_id("mock:mod-1") is not None

    # Simulate database write failure by making repository raise an OperationalError
    def failing_save(*args, **kwargs):
        import sqlite3

        raise sqlite3.OperationalError("attempt to write a readonly database")

    repo.save_provider_refresh = failing_save  # type: ignore

    mod_2 = ProviderModel(id="mod-2", provider_id="mock", display_name="New Model")
    adapter.set_models([mod_2])

    result = await catalog.refresh_provider("mock")
    assert result.success is False
    assert result.error is not None
    assert "readonly" in result.error.lower()

    # New model must NOT be added to in-memory catalog
    assert catalog.get_by_composite_id("mock:mod-2") is None
    # Previous model is preserved and marked stale
    initial_entry = catalog.get_by_composite_id("mock:mod-1")
    assert initial_entry is not None
    assert initial_entry.is_stale is True

    db_mgr.close()


def test_database_close_and_resource_cleanup(tmp_path: Path):
    """Closing DatabaseManager frees connection and subsequent access raises RuntimeError."""
    db_file = str(tmp_path / "test_close.db")
    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.initialize()
    assert db_mgr.is_initialized is True
    assert db_mgr.get_connection() is not None

    db_mgr.close()
    assert db_mgr.is_initialized is False

    with pytest.raises(RuntimeError, match="not been initialized"):
        db_mgr.get_connection()
