"""Automated unit tests for FreeFlow AI Model Catalog and Provider Management.

Validates unified model discovery, composite ID disambiguation, fault isolation,
stale entry handling, capability filtering, and empty/duplicate handling
using mock adapters without network or live daemon dependencies.
"""

import httpx
import pytest

from backend.catalog import CatalogEntry, CatalogRefreshResult, ModelCatalog
from backend.providers import (
    MockProviderAdapter,
    ModelCapability,
    OllamaAdapter,
    ProviderContext,
    ProviderModel,
    ProviderRegistry,
    ProviderUnavailableError,
)


class FailingProviderAdapter(MockProviderAdapter):
    """Adapter that intentionally fails during model listing."""

    async def list_models(self, context: ProviderContext) -> list[ProviderModel]:
        raise ProviderUnavailableError("Simulated provider outage", provider_id=self.adapter_id)


class DynamicMockAdapter(MockProviderAdapter):
    """Adapter allowing dynamic mutation of its model list between calls."""

    def __init__(self, adapter_id: str, models: list[ProviderModel]) -> None:
        super().__init__(adapter_id=adapter_id, models=models)

    def set_models(self, models: list[ProviderModel]) -> None:
        self._models = {m.id: m for m in models}


class TestModelCatalogDiscovery:
    """Tests for multi-provider discovery and aggregation."""

    @pytest.mark.anyio
    async def test_refresh_single_provider_success(self):
        registry = ProviderRegistry()
        adapter = MockProviderAdapter(adapter_id="mock-1")
        registry.register(adapter)

        catalog = ModelCatalog(registry=registry)
        result = await catalog.refresh_provider("mock-1")

        assert isinstance(result, CatalogRefreshResult)
        assert result.success is True
        assert result.provider_id == "mock-1"
        assert result.models_count >= 2

        entries = catalog.list_entries(provider_id="mock-1")
        assert len(entries) == result.models_count
        for entry in entries:
            assert isinstance(entry, CatalogEntry)
            assert entry.provider_id == "mock-1"
            assert entry.composite_id == f"mock-1:{entry.model_id}"
            assert entry.is_stale is False
            assert entry.last_seen_at is not None

    @pytest.mark.anyio
    async def test_unregistered_provider_refresh(self):
        registry = ProviderRegistry()
        catalog = ModelCatalog(registry=registry)

        result = await catalog.refresh_provider("unknown-provider")
        assert result.success is False
        assert result.models_count == 0
        assert "not registered" in (result.error or "")

    @pytest.mark.anyio
    async def test_composite_id_disambiguation_for_shared_model_names(self):
        """When two providers host a model with the same model_id, they must not collide."""
        registry = ProviderRegistry()

        shared_model_id = "llama3.2:3b"

        # Provider 1: local Ollama mock
        model_ollama = ProviderModel(
            id=shared_model_id,
            provider_id="ollama-local",
            display_name="Ollama Llama 3.2 3B",
            capabilities=ModelCapability(supports_streaming=True, supports_tools=True),
            is_local=True,
        )
        adapter_ollama = MockProviderAdapter(adapter_id="ollama-local", models=[model_ollama])
        registry.register(adapter_ollama)

        # Provider 2: remote hosted mock
        model_hosted = ProviderModel(
            id=shared_model_id,
            provider_id="hosted-cloud",
            display_name="Hosted Llama 3.2 3B",
            capabilities=ModelCapability(supports_streaming=True, supports_tools=False),
            is_local=False,
        )
        adapter_hosted = MockProviderAdapter(adapter_id="hosted-cloud", models=[model_hosted])
        registry.register(adapter_hosted)

        catalog = ModelCatalog(registry=registry)
        results = await catalog.refresh_all()
        assert len(results) == 2
        assert all(r.success for r in results)

        # Both entries must exist distinctly
        ollama_entry = catalog.get_entry("ollama-local", shared_model_id)
        assert ollama_entry is not None
        assert ollama_entry.composite_id == "ollama-local:llama3.2:3b"
        assert ollama_entry.is_local is True
        assert ollama_entry.capabilities.supports_tools is True

        hosted_entry = catalog.get_entry("hosted-cloud", shared_model_id)
        assert hosted_entry is not None
        assert hosted_entry.composite_id == "hosted-cloud:llama3.2:3b"
        assert hosted_entry.is_local is False
        assert hosted_entry.capabilities.supports_tools is False

        # Direct composite lookup
        assert catalog.get_by_composite_id("ollama-local:llama3.2:3b") is ollama_entry
        assert catalog.get_by_composite_id("hosted-cloud:llama3.2:3b") is hosted_entry

        # Find all deployments
        deployments = catalog.find_deployments(shared_model_id)
        assert len(deployments) == 2
        provider_ids = {d.provider_id for d in deployments}
        assert provider_ids == {"ollama-local", "hosted-cloud"}


class TestFaultIsolationAndStaleHandling:
    """Tests for independent provider discovery and stale entry retention."""

    @pytest.mark.anyio
    async def test_fault_isolation_failing_provider_does_not_block_healthy(self):
        registry = ProviderRegistry()

        # Healthy provider
        healthy_adapter = MockProviderAdapter(adapter_id="healthy-mock")
        registry.register(healthy_adapter)

        # Failing provider
        failing_adapter = FailingProviderAdapter(adapter_id="failing-mock")
        registry.register(failing_adapter)

        catalog = ModelCatalog(registry=registry)
        results = await catalog.refresh_all()
        assert len(results) == 2

        res_healthy = next(r for r in results if r.provider_id == "healthy-mock")
        assert res_healthy.success is True
        assert res_healthy.models_count >= 1

        res_failing = next(r for r in results if r.provider_id == "failing-mock")
        assert res_failing.success is False
        assert "Simulated provider outage" in (res_failing.error or "")

        # Healthy models are present in catalog
        healthy_entries = catalog.list_entries(provider_id="healthy-mock")
        assert len(healthy_entries) >= 1
        assert all(not e.is_stale for e in healthy_entries)

    @pytest.mark.anyio
    async def test_stale_retention_on_refresh_failure(self):
        """When an existing provider fails refresh, prior entries are marked stale, not deleted."""
        registry = ProviderRegistry()
        adapter = DynamicMockAdapter(
            adapter_id="flaky-mock",
            models=[
                ProviderModel(
                    id="flaky-model-1",
                    provider_id="flaky-mock",
                    display_name="Flaky Model 1",
                )
            ],
        )
        registry.register(adapter)

        catalog = ModelCatalog(registry=registry)

        # 1st refresh: Success
        res1 = await catalog.refresh_provider("flaky-mock")
        assert res1.success is True
        entry = catalog.get_entry("flaky-mock", "flaky-model-1")
        assert entry is not None
        assert entry.is_stale is False

        # Replace adapter with a failing one
        failing_adapter = FailingProviderAdapter(adapter_id="flaky-mock")
        registry.register(failing_adapter)

        # 2nd refresh: Fails
        res2 = await catalog.refresh_provider("flaky-mock")
        assert res2.success is False

        # Prior entry is still in catalog, but marked stale!
        entry_after_fail = catalog.get_entry("flaky-mock", "flaky-model-1")
        assert entry_after_fail is not None
        assert entry_after_fail.is_stale is True

        # Querying with include_stale=False excludes it
        active_entries = catalog.list_entries(provider_id="flaky-mock", include_stale=False)
        assert len(active_entries) == 0

        # Querying with include_stale=True includes it
        all_entries = catalog.list_entries(provider_id="flaky-mock", include_stale=True)
        assert len(all_entries) == 1

    @pytest.mark.anyio
    async def test_omitted_model_marked_stale_and_reappears(self):
        """When a model disappears from discovery, it is marked stale.

        If it returns in a subsequent discovery, stale is cleared.
        """
        registry = ProviderRegistry()
        model_a = ProviderModel(id="model-a", provider_id="dyn-mock", display_name="Model A")
        model_b = ProviderModel(id="model-b", provider_id="dyn-mock", display_name="Model B")

        adapter = DynamicMockAdapter(adapter_id="dyn-mock", models=[model_a, model_b])
        registry.register(adapter)

        catalog = ModelCatalog(registry=registry)

        # 1st refresh: both A and B present
        await catalog.refresh_provider("dyn-mock")
        assert catalog.get_entry("dyn-mock", "model-a").is_stale is False
        assert catalog.get_entry("dyn-mock", "model-b").is_stale is False

        # 2nd refresh: model B removed from provider
        adapter.set_models([model_a])
        await catalog.refresh_provider("dyn-mock")

        assert catalog.get_entry("dyn-mock", "model-a").is_stale is False
        assert catalog.get_entry("dyn-mock", "model-b").is_stale is True

        # 3rd refresh: model B re-installed
        adapter.set_models([model_a, model_b])
        await catalog.refresh_provider("dyn-mock")

        assert catalog.get_entry("dyn-mock", "model-b").is_stale is False


class TestCatalogFilteringAndDeduplication:
    """Tests for capability filtering, deduplication, and empty model lists."""

    @pytest.mark.anyio
    async def test_duplicate_model_ids_in_provider_response(self):
        """If an adapter returns duplicate model IDs, catalog deduplicates cleanly."""
        registry = ProviderRegistry()

        dup1 = ProviderModel(
            id="dup-model",
            provider_id="dup-mock",
            display_name="Duplicate Model First",
        )
        dup2 = ProviderModel(
            id="dup-model",
            provider_id="dup-mock",
            display_name="Duplicate Model Second",
        )

        adapter = MockProviderAdapter(adapter_id="dup-mock", models=[dup1, dup2])
        registry.register(adapter)

        catalog = ModelCatalog(registry=registry)
        result = await catalog.refresh_provider("dup-mock")

        assert result.success is True
        assert result.models_count == 1

        entries = catalog.list_entries(provider_id="dup-mock")
        assert len(entries) == 1
        assert entries[0].model_id == "dup-model"

    @pytest.mark.anyio
    async def test_empty_models_list(self):
        """An adapter returning an empty list should succeed with models_count=0."""
        registry = ProviderRegistry()
        adapter = MockProviderAdapter(adapter_id="empty-mock", models=[])
        registry.register(adapter)

        catalog = ModelCatalog(registry=registry)
        result = await catalog.refresh_provider("empty-mock")

        assert result.success is True
        assert result.models_count == 0
        assert catalog.list_entries(provider_id="empty-mock") == []

    @pytest.mark.anyio
    async def test_capability_and_locality_filtering(self):
        registry = ProviderRegistry()

        vision_local = ProviderModel(
            id="local-vision",
            provider_id="filter-mock",
            display_name="Local Vision",
            capabilities=ModelCapability(
                supports_vision=True, supports_tools=False, supports_streaming=True
            ),
            is_local=True,
        )
        tools_cloud = ProviderModel(
            id="cloud-tools",
            provider_id="filter-mock",
            display_name="Cloud Tools",
            capabilities=ModelCapability(
                supports_vision=False, supports_tools=True, supports_streaming=True
            ),
            is_local=False,
        )
        plain_local = ProviderModel(
            id="local-plain",
            provider_id="filter-mock",
            display_name="Local Plain",
            capabilities=ModelCapability(
                supports_vision=False, supports_tools=False, supports_streaming=False
            ),
            is_local=True,
        )

        adapter = MockProviderAdapter(
            adapter_id="filter-mock",
            models=[vision_local, tools_cloud, plain_local],
        )
        registry.register(adapter)

        catalog = ModelCatalog(registry=registry)
        await catalog.refresh_provider("filter-mock")

        # Filter by locality
        local_models = catalog.list_entries(is_local=True)
        assert {m.model_id for m in local_models} == {"local-vision", "local-plain"}

        cloud_models = catalog.list_entries(is_local=False)
        assert {m.model_id for m in cloud_models} == {"cloud-tools"}

        # Filter by vision
        vision_models = catalog.list_entries(supports_vision=True)
        assert [m.model_id for m in vision_models] == ["local-vision"]

        # Filter by tools
        tool_models = catalog.list_entries(supports_tools=True)
        assert [m.model_id for m in tool_models] == ["cloud-tools"]

        # Filter by streaming
        streaming_models = catalog.list_entries(supports_streaming=True)
        assert {m.model_id for m in streaming_models} == {
            "local-vision",
            "cloud-tools",
        }


class TestCatalogWithOllamaMockTransport:
    """Tests catalog integration with OllamaAdapter using MockTransport."""

    @pytest.mark.anyio
    async def test_catalog_refreshes_ollama_adapter(self):
        registry = ProviderRegistry()

        ollama_payload = {
            "models": [
                {
                    "name": "llama3.2:3b",
                    "details": {"family": "llama", "families": ["llama"]},
                },
                {
                    "name": "llava:7b",
                    "details": {"family": "llama", "families": ["llama", "clip"]},
                },
            ]
        }

        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_payload))
        client = httpx.AsyncClient(transport=transport)
        ollama = OllamaAdapter(adapter_id="ollama-local", http_client=client)
        registry.register(ollama)

        catalog = ModelCatalog(registry=registry)
        result = await catalog.refresh_provider("ollama-local")

        assert result.success is True
        assert result.models_count == 2

        entries = catalog.list_entries(provider_id="ollama-local")
        assert len(entries) == 2

        llama = catalog.get_entry("ollama-local", "llama3.2:3b")
        assert llama is not None
        assert llama.is_local is True
        assert llama.capabilities.supports_tools is True
        assert llama.capabilities.supports_vision is False

        llava = catalog.get_entry("ollama-local", "llava:7b")
        assert llava is not None
        assert llava.capabilities.supports_vision is True
