"""OpenAI-compatible error handling and exception mapping for FreeFlow AI.

Normalizes internal exceptions and validation errors into predictable OpenAI-format
responses without leaking prompts, message contents, or internal tracebacks.
"""

from collections.abc import Mapping

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.logger import logger
from backend.providers.errors import (
    AuthenticationError,
    ContextLengthError,
    InvalidRequestError,
    ModelNotFoundError,
    PermissionError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
    UnsupportedCapabilityError,
)
from backend.routing.engine import RoutingExhaustedError

from .models import OpenAiErrorDetail, OpenAiErrorEnvelope


def make_error_response(
    status_code: int,
    message: str,
    error_type: str,
    code: str | None = None,
    param: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build a standard OpenAI error response envelope."""
    payload = OpenAiErrorEnvelope(
        error=OpenAiErrorDetail(
            message=message,
            type=error_type,
            param=param,
            code=code,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
        headers=headers,
    )


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    """Normalize FastAPI HTTPExceptions into OpenAI error bodies."""
    detail_str = str(exc.detail)
    err_type = "invalid_request_error"
    code = None

    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        err_type = "authentication_error"
        code = "invalid_api_key"
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        err_type = "invalid_request_error"
        code = "resource_not_found"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        err_type = "permission_error"
        code = "forbidden"

    return make_error_response(
        status_code=exc.status_code,
        message=detail_str,
        error_type=err_type,
        code=code,
        headers=exc.headers,
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Normalize Pydantic request validation errors into OpenAI error bodies."""
    errors = exc.errors()
    first_err = errors[0] if errors else {}
    loc = first_err.get("loc", ())
    param = str(loc[-1]) if loc else None
    msg = first_err.get("msg", "Invalid request parameter")

    return make_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=f"Invalid parameter {param!r}: {msg}" if param else msg,
        error_type="invalid_request_error",
        code="bad_request",
        param=param,
    )


async def provider_error_handler(_: Request, exc: ProviderError) -> JSONResponse:
    """Normalize ProviderError hierarchy into appropriate HTTP status and OpenAI error shape."""
    logger.warning(
        "Provider error mapped to HTTP response",
        error_category=exc.category.value,
        status_code=exc.status_code,
        error_message=exc.message,
    )

    if isinstance(exc, ModelNotFoundError):
        return make_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=exc.message,
            error_type="invalid_request_error",
            code="model_not_found",
            param="model",
        )

    if isinstance(exc, UnsupportedCapabilityError):
        return make_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=exc.message,
            error_type="invalid_request_error",
            code="unsupported_capability",
        )

    if isinstance(exc, RoutingExhaustedError):
        return make_error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=exc.message,
            error_type="service_unavailable_error",
            code="routing_exhausted",
        )

    if isinstance(exc, AuthenticationError):
        return make_error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=exc.message,
            error_type="authentication_error",
            code="provider_auth_failure",
        )

    if isinstance(exc, PermissionError):
        return make_error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message=exc.message,
            error_type="permission_error",
            code="provider_permission_denied",
        )

    if isinstance(exc, ContextLengthError):
        return make_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=exc.message,
            error_type="invalid_request_error",
            code="context_length_exceeded",
        )

    if isinstance(exc, InvalidRequestError):
        return make_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=exc.message,
            error_type="invalid_request_error",
            code="invalid_request",
        )

    if isinstance(exc, RateLimitError):
        headers = {}
        if exc.retry_after is not None:
            headers["Retry-After"] = str(int(exc.retry_after))
        return make_error_response(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message=exc.message,
            error_type="rate_limit_error",
            code="rate_limit_exceeded",
            headers=headers,
        )

    if isinstance(exc, ProviderTimeoutError):
        return make_error_response(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            message=exc.message,
            error_type="timeout_error",
            code="gateway_timeout",
        )

    if isinstance(exc, ProviderUnavailableError):
        return make_error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=exc.message,
            error_type="service_unavailable_error",
            code="service_unavailable",
        )

    # Fallback for generic or unclassified ProviderError
    return make_error_response(
        status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY,
        message=exc.message,
        error_type="api_error",
        code="provider_error",
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all normalized error handlers on the FastAPI application."""
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ProviderError, provider_error_handler)  # type: ignore[arg-type]
