"""Provider abstraction package for FreeFlow AI.

Provides the common interface, typed request/response models, normalized error hierarchy,
and mock implementations for AI providers.
"""

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
    ContextLengthError,
    ErrorCategory,
    InvalidRequestError,
    MalformedResponseError,
    ModelNotFoundError,
    PermissionError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
    UnsupportedCapabilityError,
)
from .mock import MockProviderAdapter
from .ollama import OllamaAdapter, detect_ollama_capabilities
from .registry import ProviderRegistry, registry

__all__ = [
    "AuthenticationError",
    "ChatChoice",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatMessage",
    "ConnectionHealth",
    "ContextLengthError",
    "ErrorCategory",
    "InvalidRequestError",
    "MalformedResponseError",
    "ModelCapability",
    "ModelNotFoundError",
    "MockProviderAdapter",
    "OllamaAdapter",
    "PermissionError",
    "ProviderAdapter",
    "ProviderContext",
    "ProviderError",
    "ProviderModel",
    "ProviderRegistry",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "RateLimitError",
    "UnsupportedCapabilityError",
    "UsageInfo",
    "detect_ollama_capabilities",
    "registry",
]
