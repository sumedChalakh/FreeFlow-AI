"""Automated unit tests for FreeFlow AI Provider Abstraction (Phase 2).

Validates the common interface, typed models, error classification,
mock adapter behavior, and adapter registry without network calls.
"""

import pytest
from pydantic import ValidationError

from backend.providers import (
    AuthenticationError,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ConnectionHealth,
    ErrorCategory,
    MalformedResponseError,
    MockProviderAdapter,
    ModelCapability,
    ModelNotFoundError,
    ProviderAdapter,
    ProviderContext,
    ProviderModel,
    ProviderRegistry,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
    UsageInfo,
)


class TestProviderModels:
    """Tests for typed request, response, and capability data models."""

    def test_chat_message_valid(self):
        msg = ChatMessage(role="user", content="Hello, world!")
        assert msg.role == "user"
        assert msg.content == "Hello, world!"
        assert msg.name is None

    def test_chat_completion_request_validation(self):
        # Empty messages list should fail validation
        with pytest.raises(ValidationError):
            ChatCompletionRequest(model="test-model", messages=[])

        # Temperature outside 0.0 - 2.0 should fail
        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                model="test-model",
                messages=[ChatMessage(role="user", content="hi")],
                temperature=2.5,
            )

        # Valid request
        req = ChatCompletionRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="hi")],
            max_tokens=100,
            temperature=0.7,
            stream=False,
        )
        assert req.model == "test-model"
        assert req.max_tokens == 100
        assert req.stream is False

    def test_usage_info_unknown_vs_zero(self):
        """Verify that omitted usage is preserved as None (unknown), not fabricated zero."""
        unknown_usage = UsageInfo()
        assert unknown_usage.prompt_tokens is None
        assert unknown_usage.completion_tokens is None
        assert unknown_usage.total_tokens is None
        assert unknown_usage.is_known is False

        known_usage = UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        assert known_usage.is_known is True
        assert known_usage.total_tokens == 15

    def test_provider_model_capabilities(self):
        caps = ModelCapability(
            supports_streaming=True,
            supports_tools=False,
            supports_vision=True,
            context_window=32768,
        )
        model = ProviderModel(
            id="test-vision",
            provider_id="mock",
            display_name="Test Vision Model",
            capabilities=caps,
            is_local=False,
        )
        assert model.capabilities.supports_vision is True
        assert model.capabilities.context_window == 32768
        assert model.is_local is False


class TestErrorClassification:
    """Tests for normalized provider errors and retryability categorization."""

    def test_retryable_categories(self):
        timeout_err = ProviderTimeoutError(provider_id="mock")
        assert timeout_err.category == ErrorCategory.TIMEOUT
        assert timeout_err.is_retryable is True

        unavailable_err = ProviderUnavailableError(provider_id="mock")
        assert unavailable_err.category == ErrorCategory.UNAVAILABLE
        assert unavailable_err.is_retryable is True

        rate_limit_err = RateLimitError(provider_id="mock", retry_after=3.0)
        assert rate_limit_err.category == ErrorCategory.RATE_LIMIT
        assert rate_limit_err.retry_after == 3.0
        assert rate_limit_err.is_retryable is True

        malformed_err = MalformedResponseError(provider_id="mock")
        assert malformed_err.category == ErrorCategory.MALFORMED_RESPONSE
        assert malformed_err.is_retryable is True

    def test_non_retryable_categories(self):
        auth_err = AuthenticationError(provider_id="mock")
        assert auth_err.category == ErrorCategory.AUTH
        assert auth_err.is_retryable is False

        model_err = ModelNotFoundError(model_id="non-existent", provider_id="mock")
        assert model_err.category == ErrorCategory.UNSUPPORTED
        assert model_err.model_id == "non-existent"
        assert model_err.is_retryable is False


class TestMockProviderAdapter:
    """Tests for MockProviderAdapter behavior, failure simulation, and model discovery."""

    @pytest.fixture
    def adapter(self):
        return MockProviderAdapter(adapter_id="mock-test")

    @pytest.fixture
    def context(self):
        return ProviderContext(base_url="http://localhost:8080", timeout_seconds=5.0)

    @pytest.mark.anyio
    async def test_adapter_id(self, adapter):
        assert adapter.adapter_id == "mock-test"
        assert isinstance(adapter, ProviderAdapter)

    @pytest.mark.anyio
    async def test_list_models_success(self, adapter, context):
        models = await adapter.list_models(context)
        assert len(models) >= 2
        model_ids = [m.id for m in models]
        assert "mock-chat-v1" in model_ids

    @pytest.mark.anyio
    async def test_list_models_auth_failure(self, adapter):
        bad_context = ProviderContext(api_key="invalid-key")
        with pytest.raises(AuthenticationError):
            await adapter.list_models(bad_context)

    @pytest.mark.anyio
    async def test_test_connection_healthy(self, adapter, context):
        health = await adapter.test_connection(context)
        assert isinstance(health, ConnectionHealth)
        assert health.healthy is True
        assert health.latency_ms is not None

    @pytest.mark.anyio
    async def test_test_connection_unhealthy_auth(self, adapter):
        bad_context = ProviderContext(api_key="invalid-key")
        health = await adapter.test_connection(bad_context)
        assert health.healthy is False
        assert "invalid API key" in (health.message or "")

    @pytest.mark.anyio
    async def test_complete_chat_success(self, adapter, context):
        req = ChatCompletionRequest(
            model="mock-chat-v1",
            messages=[ChatMessage(role="user", content="Hello")],
        )
        resp = await adapter.complete_chat(context, req)
        assert isinstance(resp, ChatCompletionResponse)
        assert resp.model == "mock-chat-v1"
        assert resp.provider_id == "mock-test"
        assert len(resp.choices) == 1
        assert resp.choices[0].message.role == "assistant"
        assert resp.usage is not None
        assert resp.usage.total_tokens is not None

    @pytest.mark.anyio
    async def test_complete_chat_honest_unknown_usage(self, adapter, context):
        req = ChatCompletionRequest(
            model="mock-no-usage",
            messages=[ChatMessage(role="user", content="Hello")],
        )
        resp = await adapter.complete_chat(context, req)
        assert resp.usage is None

    @pytest.mark.anyio
    async def test_complete_chat_timeout_simulation(self, adapter, context):
        req = ChatCompletionRequest(
            model="mock-timeout",
            messages=[ChatMessage(role="user", content="Hi")],
        )
        with pytest.raises(ProviderTimeoutError) as exc_info:
            await adapter.complete_chat(context, req)
        assert exc_info.value.category == ErrorCategory.TIMEOUT

    @pytest.mark.anyio
    async def test_complete_chat_unavailable_simulation(self, adapter, context):
        req = ChatCompletionRequest(
            model="mock-unavailable",
            messages=[ChatMessage(role="user", content="Hi")],
        )
        with pytest.raises(ProviderUnavailableError) as exc_info:
            await adapter.complete_chat(context, req)
        assert exc_info.value.category == ErrorCategory.UNAVAILABLE

    @pytest.mark.anyio
    async def test_complete_chat_rate_limit_simulation(self, adapter, context):
        req = ChatCompletionRequest(
            model="mock-ratelimit",
            messages=[ChatMessage(role="user", content="Hi")],
        )
        with pytest.raises(RateLimitError) as exc_info:
            await adapter.complete_chat(context, req)
        assert exc_info.value.retry_after == 5.0

    @pytest.mark.anyio
    async def test_complete_chat_malformed_simulation(self, adapter, context):
        req = ChatCompletionRequest(
            model="mock-malformed",
            messages=[ChatMessage(role="user", content="Hi")],
        )
        with pytest.raises(MalformedResponseError):
            await adapter.complete_chat(context, req)

    @pytest.mark.anyio
    async def test_complete_chat_unknown_model(self, adapter, context):
        req = ChatCompletionRequest(
            model="unregistered-model",
            messages=[ChatMessage(role="user", content="Hi")],
        )
        with pytest.raises(ModelNotFoundError):
            await adapter.complete_chat(context, req)


class TestProviderRegistry:
    """Tests for decoupled ProviderRegistry."""

    def test_register_get_and_list(self):
        registry = ProviderRegistry()
        adapter = MockProviderAdapter(adapter_id="custom-mock")

        assert registry.list_adapters() == []
        assert registry.get("custom-mock") is None

        registry.register(adapter)
        assert registry.list_adapters() == ["custom-mock"]
        assert registry.get("custom-mock") is adapter
        assert registry.require("custom-mock") is adapter

        # require on non-existent raises KeyError
        with pytest.raises(KeyError):
            registry.require("non-existent")

        # unregister
        removed = registry.unregister("custom-mock")
        assert removed is adapter
        assert registry.get("custom-mock") is None

        # clear
        registry.register(adapter)
        registry.clear()
        assert registry.list_adapters() == []
