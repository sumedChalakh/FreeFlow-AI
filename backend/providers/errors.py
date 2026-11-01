"""Standardized error hierarchy and categories for FreeFlow AI providers.

Maps cleanly to the categories defined in docs/ROUTING_AND_FAILOVER.md.
"""

from enum import StrEnum
from typing import Any


class ErrorCategory(StrEnum):
    """Normalized error categories for provider interactions."""

    AUTH = "auth"
    PERMISSION = "permission"
    INVALID_REQUEST = "invalid_request"
    CONTEXT_LENGTH = "context_length"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    MALFORMED_RESPONSE = "malformed_response"
    UNSUPPORTED = "unsupported"


class ProviderError(Exception):
    """Base exception for all provider adapter failures."""

    def __init__(
        self,
        message: str,
        *,
        category: ErrorCategory,
        provider_id: str,
        status_code: int | None = None,
        retry_after: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.category = category
        self.provider_id = provider_id
        self.status_code = status_code
        self.retry_after = retry_after
        self.details = details or {}

    @property
    def is_retryable(self) -> bool:
        """Indicates whether this error is eligible for retry/failover under bounded budget."""
        return self.category in {
            ErrorCategory.TIMEOUT,
            ErrorCategory.UNAVAILABLE,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.MALFORMED_RESPONSE,
        }

    def __repr__(self) -> str:
        return (
            f"ProviderError(provider_id={self.provider_id!r}, "
            f"category={self.category.value!r}, "
            f"message={self.message!r}, "
            f"status_code={self.status_code})"
        )


class AuthenticationError(ProviderError):
    """Raised when authentication credentials are missing or rejected."""

    def __init__(
        self,
        message: str = "Provider authentication failed",
        *,
        provider_id: str,
        status_code: int = 401,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.AUTH,
            provider_id=provider_id,
            status_code=status_code,
            details=details,
        )


class PermissionError(ProviderError):
    """Raised when the provider account lacks permission for the requested action."""

    def __init__(
        self,
        message: str = "Provider permission denied",
        *,
        provider_id: str,
        status_code: int = 403,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.PERMISSION,
            provider_id=provider_id,
            status_code=status_code,
            details=details,
        )


class InvalidRequestError(ProviderError):
    """Raised when the request parameters are invalid from the provider's perspective."""

    def __init__(
        self,
        message: str = "Invalid request payload for provider",
        *,
        provider_id: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.INVALID_REQUEST,
            provider_id=provider_id,
            status_code=status_code,
            details=details,
        )


class ContextLengthError(ProviderError):
    """Raised when the prompt exceeds the model's context length limit."""

    def __init__(
        self,
        message: str = "Request exceeds model context window",
        *,
        provider_id: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.CONTEXT_LENGTH,
            provider_id=provider_id,
            status_code=status_code,
            details=details,
        )


class RateLimitError(ProviderError):
    """Raised when provider rate limits or quotas are exceeded."""

    def __init__(
        self,
        message: str = "Provider rate limit exceeded",
        *,
        provider_id: str,
        status_code: int = 429,
        retry_after: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.RATE_LIMIT,
            provider_id=provider_id,
            status_code=status_code,
            retry_after=retry_after,
            details=details,
        )


class ProviderTimeoutError(ProviderError):
    """Raised when a provider request times out."""

    def __init__(
        self,
        message: str = "Provider request timed out",
        *,
        provider_id: str,
        status_code: int = 504,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.TIMEOUT,
            provider_id=provider_id,
            status_code=status_code,
            details=details,
        )


class ProviderUnavailableError(ProviderError):
    """Raised when the provider is unreachable, down, or returning 5xx status."""

    def __init__(
        self,
        message: str = "Provider service unavailable",
        *,
        provider_id: str,
        status_code: int = 503,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.UNAVAILABLE,
            provider_id=provider_id,
            status_code=status_code,
            details=details,
        )


class MalformedResponseError(ProviderError):
    """Raised when the provider returns unparseable or schema-violating output."""

    def __init__(
        self,
        message: str = "Received unparseable or malformed response from provider",
        *,
        provider_id: str,
        status_code: int = 502,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.MALFORMED_RESPONSE,
            provider_id=provider_id,
            status_code=status_code,
            details=details,
        )


class UnsupportedCapabilityError(ProviderError):
    """Raised when a model or provider does not support a requested capability."""

    def __init__(
        self,
        message: str = "Model does not support requested capability",
        *,
        provider_id: str,
        status_code: int = 422,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.UNSUPPORTED,
            provider_id=provider_id,
            status_code=status_code,
            details=details,
        )


class ModelNotFoundError(ProviderError):
    """Raised when the specified model is unknown or not deployed on this provider."""

    def __init__(
        self,
        model_id: str,
        *,
        provider_id: str,
        status_code: int = 404,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            f"Model {model_id!r} not found on provider {provider_id!r}",
            category=ErrorCategory.UNSUPPORTED,
            provider_id=provider_id,
            status_code=status_code,
            details=details,
        )
        self.model_id = model_id
