"""Data models for FreeFlow AI Routing Engine and Automatic Failover.

Defines schemas for target resolution, routing profiles, cooldown states,
and structured telemetry decision events without exposing sensitive message content.
"""

import secrets
import time

from pydantic import BaseModel, Field

from backend.providers.base import ModelCapability


class TargetResolution(BaseModel):
    """Result of resolving a model identifier into provider and model components."""

    provider_id: str = Field(..., description="Provider hosting the model deployment")
    model_id: str = Field(..., description="Raw provider-specific model identifier")
    composite_id: str = Field(..., description="Normalized '<provider_id>:<model_id>' string")
    is_explicit: bool = Field(
        ...,
        description="True if caller requested an exact provider deployment (cannot failover)",
    )


class RoutingProfile(BaseModel):
    """Configuration profile defining candidate priority and capability constraints."""

    name: str = Field(..., description="Unique profile name (e.g. 'default', 'coding', 'fast')")
    description: str = Field(default="", description="Human-readable profile summary")
    candidates: list[str] = Field(
        default_factory=list,
        description="Ordered list of composite IDs or model IDs to attempt in sequence",
    )
    required_capabilities: ModelCapability = Field(
        default_factory=ModelCapability,
        description="Capability baseline required for candidates in this profile",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum failover attempts on retryable errors before exhausting",
    )
    timeout_seconds: float | None = Field(
        default=None,
        gt=0.0,
        description="Optional timeout ceiling override for operations in this profile",
    )


class FailoverAttempt(BaseModel):
    """Diagnostic record of an individual candidate invocation attempt during failover."""

    attempt_number: int = Field(..., description="1-indexed sequence number of this attempt")
    composite_id: str = Field(..., description="Target composite ID attempted")
    provider_id: str = Field(..., description="Provider attempted")
    model_id: str = Field(..., description="Model ID attempted")
    success: bool = Field(..., description="Whether this individual attempt succeeded")
    error_category: str | None = Field(
        default=None, description="Normalized error category if failed"
    )
    error_message: str | None = Field(
        default=None, description="Sanitized diagnostic message if failed (no secrets)"
    )
    is_retryable: bool = Field(
        default=False, description="Whether the encountered error was eligible for failover"
    )
    latency_ms: float = Field(default=0.0, ge=0.0, description="Attempt roundtrip latency")


class RoutingDecisionEvent(BaseModel):
    """Structured audit and telemetry event emitted for each routing invocation.

    Strictly complies with security guidelines: records latency, candidate history,
    token counts, and diagnostic codes, but NEVER logs prompts, message contents,
    or credential values.
    """

    event_id: str = Field(
        default_factory=lambda: secrets.token_hex(8),
        description="Unique telemetry identifier",
    )
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp when routing decision completed",
    )
    request_id: str | None = Field(
        default=None,
        description="Correlation ID matching incoming client request",
    )
    routing_mode: str = Field(
        ...,
        description="Routing strategy: 'explicit' or 'profile'",
    )
    requested_target: str = Field(
        ...,
        description="The target string or profile requested by caller",
    )
    profile_name: str | None = Field(
        default=None,
        description="Profile name applied, if profile-based routing was used",
    )
    selected_composite_id: str | None = Field(
        default=None,
        description="Composite ID of the deployment that successfully fulfilled the request",
    )
    selected_provider_id: str | None = Field(
        default=None,
        description="Provider ID of the successful deployment",
    )
    selected_model_id: str | None = Field(
        default=None,
        description="Model ID of the successful deployment",
    )
    attempts: int = Field(
        default=0,
        ge=0,
        description="Total invocation attempts performed (1 = direct success, >1 = failovers)",
    )
    failover_history: list[FailoverAttempt] = Field(
        default_factory=list,
        description="Chronological log of attempts and failure reasons",
    )
    success: bool = Field(
        default=False,
        description="Whether the request was ultimately fulfilled by a candidate",
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total end-to-end execution latency in milliseconds",
    )
    error_category: str | None = Field(
        default=None,
        description="Final error category if request failed all candidates",
    )
    error_message: str | None = Field(
        default=None,
        description="Sanitized diagnostic summary if request failed",
    )
    prompt_tokens: int | None = Field(
        default=None,
        description="Reported prompt tokens, or None if unknown",
    )
    completion_tokens: int | None = Field(
        default=None,
        description="Reported completion tokens, or None if unknown",
    )
    total_tokens: int | None = Field(
        default=None,
        description="Reported total tokens, or None if unknown",
    )
