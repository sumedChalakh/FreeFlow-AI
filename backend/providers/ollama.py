"""Ollama local provider adapter for FreeFlow AI.

Implements model discovery, health/connection probing, and chat completion
against local Ollama runtime instances conforming to ProviderAdapter.
"""

import contextlib
import time
import uuid
from typing import Any

import httpx

from .base import (
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
from .errors import (
    InvalidRequestError,
    MalformedResponseError,
    ModelNotFoundError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"

# Recognized model family substrings for capability normalization
_VISION_PATTERNS = ("llava", "bakllava", "moondream", "vision", "minicpm-v")
_TOOL_PATTERNS = (
    "llama3.1",
    "llama3.2",
    "mistral",
    "mixtral",
    "qwen2.5",
    "command-r",
    "hermes3",
    "firefunction",
)


def detect_ollama_capabilities(
    model_name: str,
    details: dict[str, Any] | None = None,
) -> ModelCapability:
    """Normalize model capabilities from model name and Ollama metadata.

    Conservative: unsupported capabilities are never assumed.
    Unknown context windows are preserved as None rather than fabricated.
    """
    normalized_name = model_name.lower()
    details = details or {}
    families = [f.lower() for f in details.get("families", [])]
    family = details.get("family", "").lower()
    if family and family not in families:
        families.append(family)

    # Vision detection
    supports_vision = any(pat in normalized_name for pat in _VISION_PATTERNS) or any(
        any(pat in f for pat in _VISION_PATTERNS) for f in families
    )

    # Tool calling detection
    supports_tools = any(pat in normalized_name for pat in _TOOL_PATTERNS) or any(
        any(pat in f for pat in _TOOL_PATTERNS) for f in families
    )

    # Context window: Ollama tags do not guarantee context window sizes;
    # preserve as None unless explicitly provided in metadata details.
    context_window = details.get("context_length")
    if context_window is not None:
        try:
            context_window = int(context_window)
        except (ValueError, TypeError):
            context_window = None

    return ModelCapability(
        supports_streaming=True,  # Ollama chat endpoints support streaming
        supports_tools=supports_tools,
        supports_vision=supports_vision,
        context_window=context_window,
    )


class OllamaAdapter(ProviderAdapter):
    """Adapter for the local Ollama REST API."""

    def __init__(
        self,
        *,
        adapter_id: str = "ollama",
        default_base_url: str = DEFAULT_OLLAMA_BASE_URL,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._adapter_id = adapter_id
        self._default_base_url = default_base_url.rstrip("/")
        self._http_client = http_client

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    def _get_base_url(self, context: ProviderContext) -> str:
        if context.base_url:
            return context.base_url.rstrip("/")
        return self._default_base_url

    def _create_client(self, context: ProviderContext) -> httpx.AsyncClient:
        if self._http_client is not None:
            return self._http_client
        return httpx.AsyncClient(timeout=context.timeout_seconds)

    async def list_models(self, context: ProviderContext) -> list[ProviderModel]:
        """Discover locally installed models from Ollama's /api/tags endpoint."""
        base_url = self._get_base_url(context)
        url = f"{base_url}/api/tags"
        client = self._create_client(context)

        try:
            # When using injected client, do not close it
            close_client = client is not self._http_client
            try:
                response = await client.get(url, headers=context.extra_headers)
            finally:
                if close_client:
                    await client.aclose()

            if response.status_code >= 500:
                raise ProviderUnavailableError(
                    f"Ollama server error during model discovery: HTTP {response.status_code}",
                    provider_id=self.adapter_id,
                    status_code=response.status_code,
                )
            if response.status_code != 200:
                raise InvalidRequestError(
                    f"Unexpected status from Ollama /api/tags: HTTP {response.status_code}",
                    provider_id=self.adapter_id,
                    status_code=response.status_code,
                )

            try:
                data = response.json()
            except Exception as exc:
                raise MalformedResponseError(
                    f"Invalid JSON returned from Ollama /api/tags: {exc}",
                    provider_id=self.adapter_id,
                ) from exc

            raw_models = data.get("models")
            if not isinstance(raw_models, list):
                raise MalformedResponseError(
                    "Ollama /api/tags response missing 'models' list",
                    provider_id=self.adapter_id,
                )

            models: list[ProviderModel] = []
            for item in raw_models:
                if not isinstance(item, dict):
                    continue
                name = item.get("name") or item.get("model")
                if not name or not isinstance(name, str):
                    continue

                details = item.get("details")
                caps = detect_ollama_capabilities(
                    name, details if isinstance(details, dict) else None
                )

                models.append(
                    ProviderModel(
                        id=name,
                        provider_id=self.adapter_id,
                        display_name=name,
                        capabilities=caps,
                        is_local=True,
                    )
                )

            return models

        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Timeout connecting to Ollama at {base_url}",
                provider_id=self.adapter_id,
            ) from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise ProviderUnavailableError(
                f"Failed to connect to Ollama at {base_url}: {exc}",
                provider_id=self.adapter_id,
            ) from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError(
                f"Unexpected error communicating with Ollama: {exc}",
                provider_id=self.adapter_id,
            ) from exc

    async def test_connection(self, context: ProviderContext) -> ConnectionHealth:
        """Perform a safe health and connectivity probe against Ollama."""
        base_url = self._get_base_url(context)
        client = self._create_client(context)
        start_time = time.perf_counter()

        try:
            close_client = client is not self._http_client
            try:
                # Probe root endpoint or /api/tags
                response = await client.get(f"{base_url}/", headers=context.extra_headers)
            finally:
                if close_client:
                    await client.aclose()

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            if response.status_code == 200:
                return ConnectionHealth(
                    healthy=True,
                    message="Ollama is running",
                    latency_ms=latency_ms,
                )

            return ConnectionHealth(
                healthy=False,
                message=f"Ollama returned HTTP {response.status_code}",
                latency_ms=latency_ms,
            )

        except (httpx.ConnectError, httpx.NetworkError):
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ConnectionHealth(
                healthy=False,
                message=f"Cannot reach Ollama at {base_url}. Is Ollama running?",
                latency_ms=latency_ms,
            )
        except httpx.TimeoutException:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ConnectionHealth(
                healthy=False,
                message=f"Connection to Ollama timed out after {context.timeout_seconds}s",
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ConnectionHealth(
                healthy=False,
                message=f"Connection check failed: {exc}",
                latency_ms=latency_ms,
            )

    async def complete_chat(
        self,
        context: ProviderContext,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        """Execute a non-streaming chat completion using Ollama's /api/chat."""
        base_url = self._get_base_url(context)
        url = f"{base_url}/api/chat"

        # Build payload conforming to Ollama API
        messages_payload = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        options: dict[str, Any] = {}
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.top_p is not None:
            options["top_p"] = request.top_p
        if request.stop is not None:
            options["stop"] = [request.stop] if isinstance(request.stop, str) else request.stop

        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages_payload,
            "stream": False,
        }
        if options:
            payload["options"] = options

        client = self._create_client(context)

        try:
            close_client = client is not self._http_client
            try:
                response = await client.post(url, json=payload, headers=context.extra_headers)
            finally:
                if close_client:
                    await client.aclose()

            # Handle 404 model not found
            if response.status_code == 404:
                raise ModelNotFoundError(
                    model_id=request.model,
                    provider_id=self.adapter_id,
                )

            # Handle 5xx errors
            if response.status_code >= 500:
                raise ProviderUnavailableError(
                    f"Ollama server error during chat completion: HTTP {response.status_code}",
                    provider_id=self.adapter_id,
                    status_code=response.status_code,
                )

            # Handle 4xx client errors
            if response.status_code != 200:
                raise InvalidRequestError(
                    f"Ollama rejected chat request: HTTP {response.status_code}",
                    provider_id=self.adapter_id,
                    status_code=response.status_code,
                )

            try:
                data = response.json()
            except Exception as exc:
                raise MalformedResponseError(
                    f"Invalid JSON returned from Ollama chat completion: {exc}",
                    provider_id=self.adapter_id,
                ) from exc

            # Verify response schema
            msg_obj = data.get("message")
            if not isinstance(msg_obj, dict) or "content" not in msg_obj:
                raise MalformedResponseError(
                    "Ollama response missing valid 'message' object",
                    provider_id=self.adapter_id,
                )

            content = msg_obj.get("content", "")
            role = msg_obj.get("role", "assistant")
            finish_reason = data.get("done_reason") or "stop"

            # Parse usage metadata honestly: unknown is None, not 0
            prompt_eval_count = data.get("prompt_eval_count")
            eval_count = data.get("eval_count")

            usage: UsageInfo | None = None
            if prompt_eval_count is not None or eval_count is not None:
                p_tokens = int(prompt_eval_count) if prompt_eval_count is not None else None
                c_tokens = int(eval_count) if eval_count is not None else None
                t_tokens = (
                    (p_tokens or 0) + (c_tokens or 0)
                    if (p_tokens is not None or c_tokens is not None)
                    else None
                )
                usage = UsageInfo(
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=t_tokens,
                    is_estimated=False,
                )

            return ChatCompletionResponse(
                id=f"ollama-cmpl-{uuid.uuid4().hex[:12]}",
                provider_id=self.adapter_id,
                model=data.get("model") or request.model,
                choices=[
                    ChatChoice(
                        index=0,
                        message=ChatMessage(role=role, content=content),
                        finish_reason=finish_reason,
                    )
                ],
                created_at=int(time.time()),
                usage=usage,
            )

        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Timeout waiting for Ollama chat completion from model {request.model!r}",
                provider_id=self.adapter_id,
            ) from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise ProviderUnavailableError(
                f"Failed to connect to Ollama at {base_url}: {exc}",
                provider_id=self.adapter_id,
            ) from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError(
                f"Unexpected error during Ollama chat completion: {exc}",
                provider_id=self.adapter_id,
            ) from exc

    async def aclose(self) -> None:
        """Close underlying HTTP client if configured."""
        if self._http_client is not None and not self._http_client.is_closed:
            with contextlib.suppress(Exception):
                await self._http_client.aclose()
