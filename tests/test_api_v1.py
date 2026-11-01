"""Integration tests for FreeFlow AI OpenAI-compatible v1 API endpoints.

Tests GET /v1/models, POST /v1/chat/completions, Bearer authentication,
streaming rejection, OpenAI error normalization, and privacy guarantees
using FastAPI TestClient and mock adapters.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

import backend.main as main_module
from backend.catalog.models import CatalogEntry
from backend.catalog.service import ModelCatalog
from backend.config import Settings
from backend.main import app
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
    ProviderTimeoutError,
    RateLimitError,
)
from backend.providers.registry import ProviderRegistry
from backend.routing.engine import RoutingEngine

TEST_TOKEN = "test-secret-bearer-token-12345"


class MockApiAdapter(ProviderAdapter):
    """Adapter for exercising API endpoints and error mappings."""

    def __init__(self, provider_id: str, models: list[ProviderModel]) -> None:
        self._provider_id = provider_id
        self._models = models
        self.raise_error: Exception | None = None

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
        if self.raise_error is not None:
            raise self.raise_error

        return ChatCompletionResponse(
            id=f"chatcmpl-test-{self._provider_id}",
            provider_id=self._provider_id,
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=f"API completion for {request.model}",
                    ),
                    finish_reason="stop",
                )
            ],
            usage=UsageInfo(prompt_tokens=15, completion_tokens=25, total_tokens=40),
        )


@pytest.fixture
def api_test_setup(monkeypatch):
    """Configures a populated catalog, mock adapter, and authenticated test client."""
    monkeypatch.setenv("FREEFLOW_API_TOKEN", TEST_TOKEN)
    test_settings = Settings()

    original_settings = getattr(main_module, "settings", None)
    main_module.settings = test_settings

    # Set up dedicated registry, catalog, and routing engine
    reg = ProviderRegistry()
    cat = ModelCatalog(registry=reg)

    mock_models = [
        ProviderModel(
            id="mock-chat-v1",
            provider_id="mock",
            display_name="Mock Chat V1",
            capabilities=ModelCapability(supports_streaming=True),
        ),
        ProviderModel(
            id="llama3.2:3b",
            provider_id="ollama",
            display_name="Ollama Llama 3.2 3B",
            capabilities=ModelCapability(supports_streaming=True),
            is_local=True,
        ),
    ]

    mock_adapter = MockApiAdapter("mock", [mock_models[0]])
    ollama_adapter = MockApiAdapter("ollama", [mock_models[1]])
    reg.register(mock_adapter)
    reg.register(ollama_adapter)

    for m in mock_models:
        cat._entries[f"{m.provider_id}:{m.id}"] = CatalogEntry.from_provider_model(m)

    engine = RoutingEngine(catalog=cat, registry=reg)

    # Inject into app state
    app.state.catalog = cat
    app.state.routing_engine = engine

    client = TestClient(app)

    try:
        yield {
            "client": client,
            "mock_adapter": mock_adapter,
            "ollama_adapter": ollama_adapter,
            "headers": {"Authorization": f"Bearer {TEST_TOKEN}"},
        }
    finally:
        main_module.settings = original_settings
        app.state.catalog = None
        app.state.routing_engine = None


# ============================================================================
# Authentication on /v1 Endpoints
# ============================================================================


def test_v1_models_auth_required(api_test_setup):
    """GET /v1/models must reject requests without valid Bearer token."""
    client: TestClient = api_test_setup["client"]

    # No token
    res = client.get("/v1/models")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    data = res.json()
    assert "error" in data
    assert data["error"]["type"] == "authentication_error"
    assert data["error"]["code"] == "invalid_api_key"

    # Wrong token
    res2 = client.get("/v1/models", headers={"Authorization": "Bearer bad-token"})
    assert res2.status_code == status.HTTP_401_UNAUTHORIZED
    assert res2.json()["error"]["code"] == "invalid_api_key"


def test_v1_chat_completions_auth_required(api_test_setup):
    """POST /v1/chat/completions must reject unauthenticated requests."""
    client: TestClient = api_test_setup["client"]
    payload = {
        "model": "default",
        "messages": [{"role": "user", "content": "Hello"}],
    }

    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    assert res.json()["error"]["type"] == "authentication_error"


# ============================================================================
# GET /v1/models Endpoint
# ============================================================================


def test_v1_models_list_success(api_test_setup):
    """GET /v1/models returns routing profiles and catalog entries in OpenAI format."""
    client: TestClient = api_test_setup["client"]
    headers = api_test_setup["headers"]

    res = client.get("/v1/models", headers=headers)
    assert res.status_code == status.HTTP_200_OK

    body = res.json()
    assert body["object"] == "list"
    ids = [item["id"] for item in body["data"]]

    # Standard routing aliases present
    assert "default" in ids
    assert "coding" in ids
    assert "fast" in ids
    assert "reasoning" in ids

    # Discovered catalog models present
    assert "mock:mock-chat-v1" in ids
    assert "mock-chat-v1" in ids
    assert "ollama:llama3.2:3b" in ids
    assert "llama3.2:3b" in ids


# ============================================================================
# POST /v1/chat/completions Endpoint
# ============================================================================


def test_v1_chat_completions_success(api_test_setup):
    """POST /v1/chat/completions executes non-streaming chat completion."""
    client: TestClient = api_test_setup["client"]
    headers = api_test_setup["headers"]

    payload = {
        "model": "mock:mock-chat-v1",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is 2+2?"},
        ],
        "temperature": 0.7,
        "max_tokens": 100,
    }

    res = client.post("/v1/chat/completions", json=payload, headers=headers)
    assert res.status_code == status.HTTP_200_OK

    data = res.json()
    assert data["object"] == "chat.completion"
    assert data["model"] == "mock-chat-v1"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert "API completion" in data["choices"][0]["message"]["content"]
    assert data["choices"][0]["finish_reason"] == "stop"

    # Verify usage fields
    assert data["usage"]["prompt_tokens"] == 15
    assert data["usage"]["completion_tokens"] == 25
    assert data["usage"]["total_tokens"] == 40


def test_v1_chat_completions_colon_model_tag(api_test_setup):
    """POST /v1/chat/completions routes successfully using colon-containing model tags."""
    client: TestClient = api_test_setup["client"]
    headers = api_test_setup["headers"]

    payload = {
        "model": "ollama:llama3.2:3b",
        "messages": [{"role": "user", "content": "Test prompt"}],
    }

    res = client.post("/v1/chat/completions", json=payload, headers=headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["model"] == "llama3.2:3b"


def test_v1_chat_completions_profile_routing(api_test_setup):
    """POST /v1/chat/completions routes successfully via profile alias 'default'."""
    client: TestClient = api_test_setup["client"]
    headers = api_test_setup["headers"]

    payload = {
        "model": "default",
        "messages": [{"role": "user", "content": "Routing test"}],
    }

    res = client.post("/v1/chat/completions", json=payload, headers=headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["object"] == "chat.completion"


# ============================================================================
# Streaming Rejection (Honest Unsupported Status)
# ============================================================================


def test_v1_chat_completions_stream_rejected_honestly(api_test_setup):
    """POST /v1/chat/completions rejects stream=True with 400 and clear error."""
    client: TestClient = api_test_setup["client"]
    headers = api_test_setup["headers"]

    payload = {
        "model": "default",
        "messages": [{"role": "user", "content": "Streaming test"}],
        "stream": True,
    }

    res = client.post("/v1/chat/completions", json=payload, headers=headers)
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    err = res.json()["error"]
    assert "Streaming is not currently supported" in err["message"]
    assert err["type"] == "invalid_request_error"


# ============================================================================
# Error Normalization & Privacy
# ============================================================================


def test_v1_chat_completions_unknown_model_returns_404(api_test_setup):
    """Requesting an unknown model returns 404 with normalized OpenAI error."""
    client: TestClient = api_test_setup["client"]
    headers = api_test_setup["headers"]

    payload = {
        "model": "non-existent-model-xyz",
        "messages": [{"role": "user", "content": "Hello"}],
    }

    res = client.post("/v1/chat/completions", json=payload, headers=headers)
    assert res.status_code == status.HTTP_404_NOT_FOUND

    data = res.json()
    assert data["error"]["type"] == "invalid_request_error"
    assert data["error"]["code"] == "model_not_found"
    assert data["error"]["param"] == "model"


def test_v1_chat_completions_validation_error_returns_400(api_test_setup):
    """Validation failure (e.g. empty messages) returns 400 with param identified."""
    client: TestClient = api_test_setup["client"]
    headers = api_test_setup["headers"]

    payload = {
        "model": "default",
        "messages": [],  # Empty messages violated min_length=1
    }

    res = client.post("/v1/chat/completions", json=payload, headers=headers)
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    data = res.json()
    assert data["error"]["type"] == "invalid_request_error"
    assert data["error"]["code"] == "bad_request"
    assert data["error"]["param"] == "messages"


def test_v1_chat_completions_timeout_maps_to_504(api_test_setup):
    """ProviderTimeoutError maps to HTTP 504 with timeout_error type."""
    adapter: MockApiAdapter = api_test_setup["mock_adapter"]
    adapter.raise_error = ProviderTimeoutError("Gateway connection timed out", provider_id="mock")

    client: TestClient = api_test_setup["client"]
    headers = api_test_setup["headers"]

    payload = {
        "model": "mock:mock-chat-v1",
        "messages": [{"role": "user", "content": "Timeout test"}],
    }

    res = client.post("/v1/chat/completions", json=payload, headers=headers)
    assert res.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    data = res.json()
    assert data["error"]["type"] == "timeout_error"
    assert data["error"]["code"] == "gateway_timeout"


def test_v1_chat_completions_rate_limit_maps_to_429(api_test_setup):
    """RateLimitError maps to HTTP 429 with Retry-After header."""
    adapter: MockApiAdapter = api_test_setup["mock_adapter"]
    adapter.raise_error = RateLimitError(
        "Rate limit exceeded",
        provider_id="mock",
        retry_after=45.0,
    )

    client: TestClient = api_test_setup["client"]
    headers = api_test_setup["headers"]

    payload = {
        "model": "mock:mock-chat-v1",
        "messages": [{"role": "user", "content": "Rate limit test"}],
    }

    res = client.post("/v1/chat/completions", json=payload, headers=headers)
    assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert res.headers.get("retry-after") == "45"
    data = res.json()
    assert data["error"]["type"] == "rate_limit_error"


def test_v1_chat_completions_privacy_no_prompt_leaks(api_test_setup):
    """Error responses must not reflect prompt or message text."""
    adapter: MockApiAdapter = api_test_setup["mock_adapter"]
    adapter.raise_error = ProviderTimeoutError("Backend timeout", provider_id="mock")

    client: TestClient = api_test_setup["client"]
    headers = api_test_setup["headers"]

    confidential_prompt = "TOP_SECRET_PROMPT_KEY_12345"
    payload = {
        "model": "mock:mock-chat-v1",
        "messages": [{"role": "user", "content": confidential_prompt}],
    }

    res = client.post("/v1/chat/completions", json=payload, headers=headers)
    body_str = res.text

    assert confidential_prompt not in body_str
