"""Deterministic mock provider adapter for tests and local development.

Simulates provider behavior, failure modes, model discovery, and usage metrics
without requiring external networks, live credentials, or daemon processes.
"""

import time
import uuid

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
    AuthenticationError,
    MalformedResponseError,
    ModelNotFoundError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)


class MockProviderAdapter(ProviderAdapter):
    """Mock implementation of ProviderAdapter for deterministic testing."""

    def __init__(
        self,
        *,
        adapter_id: str = "mock",
        models: list[ProviderModel] | None = None,
        default_reply: str = "This is a mock assistant response.",
    ) -> None:
        self._adapter_id = adapter_id
        self._default_reply = default_reply

        if models is not None:
            self._models = {m.id: m for m in models}
        else:
            default_models = [
                ProviderModel(
                    id="mock-chat-v1",
                    provider_id=self._adapter_id,
                    display_name="Mock Chat v1",
                    capabilities=ModelCapability(
                        supports_streaming=True,
                        supports_tools=True,
                        supports_vision=False,
                        context_window=8192,
                    ),
                    is_local=True,
                ),
                ProviderModel(
                    id="mock-vision-v1",
                    provider_id=self._adapter_id,
                    display_name="Mock Vision v1",
                    capabilities=ModelCapability(
                        supports_streaming=True,
                        supports_tools=False,
                        supports_vision=True,
                        context_window=16384,
                    ),
                    is_local=False,
                ),
                ProviderModel(
                    id="mock-no-usage",
                    provider_id=self._adapter_id,
                    display_name="Mock Model Without Usage Stats",
                    capabilities=ModelCapability(
                        supports_streaming=False,
                        supports_tools=False,
                        supports_vision=False,
                        context_window=4096,
                    ),
                    is_local=True,
                ),
            ]
            self._models = {m.id: m for m in default_models}

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    def add_model(self, model: ProviderModel) -> None:
        """Register an additional model in this mock adapter."""
        self._models[model.id] = model

    async def list_models(self, context: ProviderContext) -> list[ProviderModel]:
        """Return the inventory of mock models."""
        if context.api_key == "invalid-key":
            raise AuthenticationError(
                "Invalid credentials provided to mock provider",
                provider_id=self.adapter_id,
            )
        return list(self._models.values())

    async def test_connection(self, context: ProviderContext) -> ConnectionHealth:
        """Probe mock provider connectivity."""
        if context.api_key == "invalid-key":
            return ConnectionHealth(
                healthy=False,
                message="Mock connection check failed: invalid API key",
                latency_ms=2.0,
            )
        if context.base_url and "unreachable" in context.base_url:
            return ConnectionHealth(
                healthy=False,
                message="Mock connection check failed: unreachable host",
                latency_ms=10.0,
            )
        return ConnectionHealth(
            healthy=True,
            message="Mock provider operational",
            latency_ms=1.2,
        )

    async def complete_chat(
        self,
        context: ProviderContext,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        """Simulate chat completion with deterministic responses and simulated failure modes."""
        # Simulated auth check
        if context.api_key == "invalid-key":
            raise AuthenticationError(
                "Mock authentication rejected: invalid API key",
                provider_id=self.adapter_id,
            )

        # Failure mode triggers based on model name
        if request.model == "mock-timeout":
            raise ProviderTimeoutError(
                "Simulated timeout on mock provider",
                provider_id=self.adapter_id,
            )
        if request.model == "mock-unavailable":
            raise ProviderUnavailableError(
                "Simulated 503 service unavailable on mock provider",
                provider_id=self.adapter_id,
            )
        if request.model == "mock-ratelimit":
            raise RateLimitError(
                "Simulated rate limit exceeded on mock provider",
                provider_id=self.adapter_id,
                retry_after=5.0,
            )
        if request.model == "mock-malformed":
            raise MalformedResponseError(
                "Simulated malformed response payload from mock provider",
                provider_id=self.adapter_id,
            )

        # Check model existence
        if request.model not in self._models:
            raise ModelNotFoundError(
                model_id=request.model,
                provider_id=self.adapter_id,
            )

        # Compute or omit usage
        usage: UsageInfo | None
        if request.model == "mock-no-usage":
            usage = None
        else:
            # Deterministic token calculations for testing
            prompt_chars = sum(len(m.content) for m in request.messages)
            prompt_tokens = max(1, prompt_chars // 4)
            completion_tokens = max(1, len(self._default_reply) // 4)
            usage = UsageInfo(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                is_estimated=False,
            )

        return ChatCompletionResponse(
            id=f"mock-cmpl-{uuid.uuid4().hex[:8]}",
            provider_id=self.adapter_id,
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=self._default_reply,
                    ),
                    finish_reason="stop",
                )
            ],
            created_at=int(time.time()),
            usage=usage,
        )
