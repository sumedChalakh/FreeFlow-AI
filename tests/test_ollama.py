"""Automated unit tests for Ollama Provider Adapter (Phase 2 P2-T3 & P2-T5).

Tests model discovery, capability normalization, connection probing,
chat completions, usage handling, and error taxonomy mapping using httpx.MockTransport.
Zero internet or live daemon dependencies required.
"""

import json

import httpx
import pytest

from backend.providers import (
    ChatCompletionRequest,
    ChatMessage,
    ConnectionHealth,
    ErrorCategory,
    InvalidRequestError,
    MalformedResponseError,
    ModelNotFoundError,
    OllamaAdapter,
    ProviderContext,
    ProviderTimeoutError,
    ProviderUnavailableError,
    detect_ollama_capabilities,
)


class TestOllamaCapabilityDetection:
    """Tests for capability metadata normalization (P2-T5)."""

    def test_vision_model_detection(self):
        # Known vision models
        caps_llava = detect_ollama_capabilities("llava:latest")
        assert caps_llava.supports_vision is True
        assert caps_llava.supports_streaming is True

        caps_moondream = detect_ollama_capabilities("moondream2:latest")
        assert caps_moondream.supports_vision is True

        caps_llama_vis = detect_ollama_capabilities("llama3.2-vision:11b")
        assert caps_llama_vis.supports_vision is True

    def test_tool_calling_model_detection(self):
        # Known tool calling models
        caps_llama31 = detect_ollama_capabilities("llama3.1:8b")
        assert caps_llama31.supports_tools is True
        assert caps_llama31.supports_vision is False

        caps_qwen = detect_ollama_capabilities("qwen2.5:7b")
        assert caps_qwen.supports_tools is True

        caps_mistral = detect_ollama_capabilities("my-custom-model", details={"family": "mistral"})
        assert caps_mistral.supports_tools is True

    def test_standard_model_without_vision_or_tools(self):
        # Standard older model
        caps = detect_ollama_capabilities("llama2:7b")
        assert caps.supports_streaming is True
        assert caps.supports_vision is False
        assert caps.supports_tools is False
        assert caps.context_window is None

    def test_context_window_handling(self):
        # When context length is absent: None (unknown, not zero)
        caps_unknown = detect_ollama_capabilities("llama3.2:3b")
        assert caps_unknown.context_window is None

        # When context length is explicitly supplied in details
        caps_known = detect_ollama_capabilities("llama3.2:3b", details={"context_length": 131072})
        assert caps_known.context_window == 131072


class TestOllamaModelDiscovery:
    """Tests for model discovery via /api/tags (P2-T3)."""

    @pytest.mark.anyio
    async def test_list_models_success(self):
        mock_tags_payload = {
            "models": [
                {
                    "name": "llama3.2:latest",
                    "model": "llama3.2:latest",
                    "details": {"family": "llama", "families": ["llama"]},
                },
                {
                    "name": "llava:13b",
                    "model": "llava:13b",
                    "details": {"family": "llama", "families": ["llama", "clip"]},
                },
            ]
        }

        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=mock_tags_payload))
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)
        context = ProviderContext()

        models = await adapter.list_models(context)
        assert len(models) == 2

        llama = next(m for m in models if m.id == "llama3.2:latest")
        assert llama.is_local is True
        assert llama.provider_id == "ollama"
        assert llama.capabilities.supports_tools is True
        assert llama.capabilities.supports_vision is False

        llava = next(m for m in models if m.id == "llava:13b")
        assert llava.is_local is True
        assert llava.capabilities.supports_vision is True

    @pytest.mark.anyio
    async def test_list_models_empty(self):
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"models": []}))
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        models = await adapter.list_models(ProviderContext())
        assert models == []

    @pytest.mark.anyio
    async def test_list_models_server_error(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(500, text="Internal Server Error")
        )
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        with pytest.raises(ProviderUnavailableError) as exc_info:
            await adapter.list_models(ProviderContext())
        assert exc_info.value.category == ErrorCategory.UNAVAILABLE
        assert exc_info.value.status_code == 500

    @pytest.mark.anyio
    async def test_list_models_malformed_json(self):
        transport = httpx.MockTransport(lambda req: httpx.Response(200, text="not-valid-json{"))
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        with pytest.raises(MalformedResponseError):
            await adapter.list_models(ProviderContext())

    @pytest.mark.anyio
    async def test_list_models_missing_models_key(self):
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"status": "ok"}))
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        with pytest.raises(MalformedResponseError):
            await adapter.list_models(ProviderContext())


class TestOllamaConnectionProbe:
    """Tests for connection and health testing."""

    @pytest.mark.anyio
    async def test_connection_healthy(self):
        transport = httpx.MockTransport(lambda req: httpx.Response(200, text="Ollama is running"))
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        health = await adapter.test_connection(ProviderContext())
        assert isinstance(health, ConnectionHealth)
        assert health.healthy is True
        assert "Ollama is running" in (health.message or "")
        assert health.latency_ms is not None

    @pytest.mark.anyio
    async def test_connection_unhealthy_non_200(self):
        transport = httpx.MockTransport(lambda req: httpx.Response(502, text="Bad Gateway"))
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        health = await adapter.test_connection(ProviderContext())
        assert health.healthy is False
        assert "502" in (health.message or "")

    @pytest.mark.anyio
    async def test_connection_offline(self):
        def raise_connect_error(req):
            raise httpx.ConnectError("Connection refused")

        transport = httpx.MockTransport(raise_connect_error)
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        health = await adapter.test_connection(ProviderContext())
        assert health.healthy is False
        assert "Cannot reach Ollama" in (health.message or "")

    @pytest.mark.anyio
    async def test_connection_timeout(self):
        def raise_timeout(req):
            raise httpx.ReadTimeout("Timeout")

        transport = httpx.MockTransport(raise_timeout)
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        health = await adapter.test_connection(ProviderContext(timeout_seconds=2.0))
        assert health.healthy is False
        assert "timed out" in (health.message or "")


class TestOllamaChatCompletion:
    """Tests for chat completions and usage handling."""

    @pytest.mark.anyio
    async def test_complete_chat_success_with_usage(self):
        mock_response = {
            "model": "llama3.2:latest",
            "message": {
                "role": "assistant",
                "content": "The sky is blue due to Rayleigh scattering.",
            },
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 14,
            "eval_count": 28,
        }

        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=mock_response))
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        req = ChatCompletionRequest(
            model="llama3.2:latest",
            messages=[ChatMessage(role="user", content="Why is the sky blue?")],
            max_tokens=150,
            temperature=0.7,
        )

        resp = await adapter.complete_chat(ProviderContext(), req)
        assert resp.model == "llama3.2:latest"
        assert resp.provider_id == "ollama"
        assert len(resp.choices) == 1
        assert resp.choices[0].message.content == "The sky is blue due to Rayleigh scattering."
        assert resp.choices[0].finish_reason == "stop"

        assert resp.usage is not None
        assert resp.usage.prompt_tokens == 14
        assert resp.usage.completion_tokens == 28
        assert resp.usage.total_tokens == 42
        assert resp.usage.is_known is True

    @pytest.mark.anyio
    async def test_complete_chat_options_passed(self):
        captured_payload = {}

        def handler(req: httpx.Request):
            nonlocal captured_payload
            captured_payload = json.loads(req.content)
            return httpx.Response(
                200,
                json={
                    "model": "llama3.2:latest",
                    "message": {"role": "assistant", "content": "Hello!"},
                    "done": True,
                },
            )

        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        req = ChatCompletionRequest(
            model="llama3.2:latest",
            messages=[ChatMessage(role="user", content="Hi")],
            max_tokens=50,
            temperature=0.2,
            top_p=0.85,
            stop=["\n"],
        )

        await adapter.complete_chat(ProviderContext(), req)

        assert captured_payload["model"] == "llama3.2:latest"
        assert captured_payload["stream"] is False
        options = captured_payload["options"]
        assert options["num_predict"] == 50
        assert options["temperature"] == 0.2
        assert options["top_p"] == 0.85
        assert options["stop"] == ["\n"]

    @pytest.mark.anyio
    async def test_complete_chat_honest_missing_usage(self):
        """Ollama responses without prompt_eval_count/eval_count must leave usage as None."""
        mock_response = {
            "model": "llama3.2:latest",
            "message": {
                "role": "assistant",
                "content": "No usage counts in this response.",
            },
            "done": True,
        }

        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=mock_response))
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        req = ChatCompletionRequest(
            model="llama3.2:latest",
            messages=[ChatMessage(role="user", content="Hello")],
        )

        resp = await adapter.complete_chat(ProviderContext(), req)
        assert resp.usage is None

    @pytest.mark.anyio
    async def test_complete_chat_model_not_found_404(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(404, json={"error": "model 'non-existent' not found"})
        )
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        req = ChatCompletionRequest(
            model="non-existent",
            messages=[ChatMessage(role="user", content="Hello")],
        )

        with pytest.raises(ModelNotFoundError) as exc_info:
            await adapter.complete_chat(ProviderContext(), req)
        assert exc_info.value.model_id == "non-existent"
        assert exc_info.value.category == ErrorCategory.UNSUPPORTED
        assert exc_info.value.status_code == 404

    @pytest.mark.anyio
    async def test_complete_chat_timeout(self):
        def raise_timeout(req):
            raise httpx.ReadTimeout("Timeout")

        transport = httpx.MockTransport(raise_timeout)
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        req = ChatCompletionRequest(
            model="llama3.2:latest",
            messages=[ChatMessage(role="user", content="Hello")],
        )

        with pytest.raises(ProviderTimeoutError) as exc_info:
            await adapter.complete_chat(ProviderContext(), req)
        assert exc_info.value.category == ErrorCategory.TIMEOUT
        assert exc_info.value.is_retryable is True

    @pytest.mark.anyio
    async def test_complete_chat_server_error(self):
        transport = httpx.MockTransport(lambda req: httpx.Response(500, text="CUDA error"))
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        req = ChatCompletionRequest(
            model="llama3.2:latest",
            messages=[ChatMessage(role="user", content="Hello")],
        )

        with pytest.raises(ProviderUnavailableError) as exc_info:
            await adapter.complete_chat(ProviderContext(), req)
        assert exc_info.value.category == ErrorCategory.UNAVAILABLE
        assert exc_info.value.status_code == 500

    @pytest.mark.anyio
    async def test_complete_chat_client_error(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(400, json={"error": "bad request"})
        )
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        req = ChatCompletionRequest(
            model="llama3.2:latest",
            messages=[ChatMessage(role="user", content="Hello")],
        )

        with pytest.raises(InvalidRequestError) as exc_info:
            await adapter.complete_chat(ProviderContext(), req)
        assert exc_info.value.category == ErrorCategory.INVALID_REQUEST
        assert exc_info.value.status_code == 400

    @pytest.mark.anyio
    async def test_complete_chat_malformed_response_schema(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"done": True})  # missing 'message'
        )
        client = httpx.AsyncClient(transport=transport)
        adapter = OllamaAdapter(http_client=client)

        req = ChatCompletionRequest(
            model="llama3.2:latest",
            messages=[ChatMessage(role="user", content="Hello")],
        )

        with pytest.raises(MalformedResponseError):
            await adapter.complete_chat(ProviderContext(), req)
