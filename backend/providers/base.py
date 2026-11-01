"""Base models, protocols, and interfaces for FreeFlow AI provider adapters.

These types define the shared contracts for model discovery, connection verification,
and chat completion across all provider implementations.
"""

import time
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message within a chat completion request or response."""

    role: str = Field(..., description="Message role (e.g. 'system', 'user', 'assistant')")
    content: str = Field(..., description="Text content of the message")
    name: str | None = Field(default=None, description="Optional author identifier")


class ChatCompletionRequest(BaseModel):
    """Normalized chat completion request passed to provider adapters."""

    model: str = Field(..., description="Target model identifier")
    messages: list[ChatMessage] = Field(
        ..., min_length=1, description="Ordered conversation history"
    )
    max_tokens: int | None = Field(
        default=None, ge=1, description="Upper bound on generated tokens"
    )
    temperature: float | None = Field(
        default=None, ge=0.0, le=2.0, description="Sampling temperature"
    )
    top_p: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Nucleus sampling probability"
    )
    stream: bool = Field(default=False, description="Whether token streaming is requested")
    stop: list[str] | str | None = Field(default=None, description="Stop sequence(s)")


class UsageInfo(BaseModel):
    """Token consumption metadata.

    Per product requirements, missing provider counts are represented as None (unknown),
    never fabricated or defaulted to zero.
    """

    prompt_tokens: int | None = Field(default=None, description="Input tokens used, if reported")
    completion_tokens: int | None = Field(
        default=None, description="Generated tokens used, if reported"
    )
    total_tokens: int | None = Field(default=None, description="Total tokens used, if reported")
    is_estimated: bool = Field(default=False, description="Whether counts are locally estimated")

    @property
    def is_known(self) -> bool:
        """Indicates if any concrete token count was provided."""
        return self.total_tokens is not None or self.prompt_tokens is not None


class ChatChoice(BaseModel):
    """A generated choice within a chat completion response."""

    index: int = Field(default=0, description="Choice index")
    message: ChatMessage = Field(..., description="Generated assistant message")
    finish_reason: str | None = Field(default="stop", description="Reason generation terminated")


class ChatCompletionResponse(BaseModel):
    """Normalized chat completion response returned by provider adapters."""

    id: str = Field(..., description="Unique response identifier")
    provider_id: str = Field(..., description="ID of the provider fulfilling the request")
    model: str = Field(..., description="Model ID that generated the completion")
    choices: list[ChatChoice] = Field(..., min_length=1, description="Generated choices")
    created_at: int = Field(default_factory=lambda: int(time.time()), description="Unix timestamp")
    usage: UsageInfo | None = Field(default=None, description="Token usage, or None if omitted")


class ModelCapability(BaseModel):
    """Capabilities supported by a specific model deployment."""

    supports_streaming: bool = Field(default=False, description="Supports SSE token streaming")
    supports_tools: bool = Field(default=False, description="Supports function/tool calling")
    supports_vision: bool = Field(default=False, description="Supports image/multimodal inputs")
    context_window: int | None = Field(
        default=None, ge=1, description="Context window tokens, if known"
    )


class ProviderModel(BaseModel):
    """Metadata representing a model available through an adapter."""

    id: str = Field(..., description="Model identifier used in API requests")
    provider_id: str = Field(..., description="Adapter/provider managing this model")
    display_name: str = Field(..., description="Human-readable model name")
    capabilities: ModelCapability = Field(
        default_factory=ModelCapability, description="Model features"
    )
    is_local: bool = Field(
        default=False, description="True if hosted on local hardware (e.g. Ollama)"
    )


class ConnectionHealth(BaseModel):
    """Result of a provider connectivity / health check."""

    healthy: bool = Field(..., description="Whether the provider is reachable and operational")
    message: str | None = Field(default=None, description="Diagnostic summary or safe error detail")
    latency_ms: float | None = Field(
        default=None, ge=0.0, description="Roundtrip check latency in milliseconds"
    )


class ProviderContext(BaseModel):
    """Runtime execution context provided to an adapter call.

    Supplies endpoints and credentials without exposing them in unredacted logs.
    """

    base_url: str | None = Field(
        default=None, description="Custom base URL for the provider endpoint"
    )
    timeout_seconds: float = Field(
        default=30.0, gt=0.0, description="Request timeout ceiling in seconds"
    )
    api_key: str | None = Field(default=None, description="Secret credential token or key")
    extra_headers: dict[str, str] = Field(default_factory=dict, description="Additional headers")


class ProviderAdapter(ABC):
    """Abstract base protocol for all FreeFlow AI provider adapters.

    Every concrete adapter (mock, Ollama, OpenAI, Anthropic, etc.) implements this interface.
    Core routing and higher-level gateways call this contract without vendor-specific branching.
    """

    @property
    @abstractmethod
    def adapter_id(self) -> str:
        """Unique identifier of the adapter (e.g., 'mock', 'ollama', 'openai')."""
        ...

    @abstractmethod
    async def list_models(self, context: ProviderContext) -> list[ProviderModel]:
        """Discover models provided by this adapter."""
        ...

    @abstractmethod
    async def test_connection(self, context: ProviderContext) -> ConnectionHealth:
        """Perform a safe health/connectivity probe."""
        ...

    @abstractmethod
    async def complete_chat(
        self,
        context: ProviderContext,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        """Execute a non-streaming chat completion."""
        ...
