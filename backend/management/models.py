"""Pydantic data models for the FreeFlow AI Management API (/api).

Provides typed schemas for provider management, connection health testing,
model catalog browsing and refreshing, routing profile inspection, and gateway diagnostics.
Never exposes raw credentials, tokens, or sensitive prompt contents.
"""

from pydantic import BaseModel, Field


class ProviderItem(BaseModel):
    """Metadata representing a registered provider adapter."""

    id: str = Field(..., description="Unique provider/adapter identifier (e.g. 'ollama', 'mock')")
    display_name: str = Field(..., description="Human-friendly provider name")
    enabled: bool = Field(default=True, description="Whether this provider is currently enabled")
    base_url: str | None = Field(default=None, description="Configured endpoint base URL, if any")
    has_credential: bool = Field(
        default=False, description="Whether credential material is configured (key never revealed)"
    )
    local: bool = Field(
        default=False, description="Whether this provider runs locally (e.g. Ollama)"
    )


class ProviderListResponse(BaseModel):
    """List of registered providers."""

    data: list[ProviderItem] = Field(..., description="Registered provider entries")


class ProviderTestResponse(BaseModel):
    """Result of testing connectivity to a specific provider adapter."""

    provider_id: str = Field(..., description="Tested provider identifier")
    status: str = Field(
        ..., description="Connectivity health status ('healthy', 'unhealthy', 'error')"
    )
    latency_ms: float | None = Field(
        default=None, description="Roundtrip check latency in milliseconds, if measured"
    )
    error: str | None = Field(
        default=None, description="Sanitized error description, or None if healthy"
    )


class ModelCapabilitySchema(BaseModel):
    """Capabilities supported by a specific catalog model."""

    supports_streaming: bool = Field(default=False, description="Supports SSE token streaming")
    supports_tools: bool = Field(default=False, description="Supports function/tool calling")
    supports_vision: bool = Field(default=False, description="Supports image/multimodal inputs")
    context_window: int | None = Field(
        default=None, description="Context window tokens, or None if unknown"
    )


class CatalogModelItem(BaseModel):
    """A normalized model deployment available in the model catalog."""

    composite_id: str = Field(
        ..., description="Unique composite model identifier ('<provider_id>:<model_id>')"
    )
    provider_id: str = Field(..., description="Provider hosting this deployment")
    model_id: str = Field(..., description="Raw model identifier from provider")
    display_name: str = Field(..., description="Human-readable model name")
    is_local: bool = Field(default=False, description="Whether model runs on local hardware")
    capabilities: ModelCapabilitySchema = Field(..., description="Model capabilities")
    is_stale: bool = Field(
        default=False, description="True if omitted from latest discovery or awaiting fresh refresh"
    )
    last_seen_at: float | None = Field(
        default=None, description="Unix timestamp when model was last discovered"
    )
    last_checked_at: float | None = Field(
        default=None, description="Unix timestamp of latest refresh check"
    )


class CatalogListResponse(BaseModel):
    """List of catalog entries for dashboard browsing."""

    data: list[CatalogModelItem] = Field(..., description="Catalog model entries")


class CatalogRefreshRequestPayload(BaseModel):
    """Optional payload for requesting catalog refresh."""

    provider_id: str | None = Field(
        default=None,
        description="Optional provider ID to refresh single provider; refreshes all if omitted",
    )


class ProviderRefreshSummary(BaseModel):
    """Summary of a refresh operation for a single provider."""

    provider_id: str = Field(..., description="Provider identifier")
    success: bool = Field(..., description="Whether discovery succeeded")
    models_count: int = Field(..., description="Number of models discovered or retained")
    error: str | None = Field(
        default=None, description="Sanitized error message if refresh failed"
    )
    timestamp: float = Field(..., description="Unix timestamp of refresh execution")


class CatalogRefreshResponse(BaseModel):
    """Result of catalog refresh operation."""

    total_refreshed: int = Field(..., description="Total number of providers attempted")
    successful_refreshes: int = Field(..., description="Number of providers refreshed successfully")
    failed_refreshes: int = Field(..., description="Number of providers that failed refresh")
    results: list[ProviderRefreshSummary] = Field(
        ..., description="Per-provider refresh summary entries"
    )


class RoutingProfileItem(BaseModel):
    """Metadata representing a routing profile."""

    name: str = Field(..., description="Profile identifier (e.g. 'default', 'coding')")
    description: str = Field(..., description="Description of the profile's purpose")
    candidates: list[str] = Field(
        ..., description="Ordered candidate deployment identifiers or aliases"
    )
    max_retries: int = Field(default=2, description="Maximum retry budget for this profile")
    timeout_seconds: float | None = Field(
        default=30.0, description="Request timeout ceiling in seconds"
    )
    required_capabilities: ModelCapabilitySchema = Field(
        ..., description="Capabilities required from candidates"
    )


class ProfileListResponse(BaseModel):
    """List of registered routing profiles."""

    data: list[RoutingProfileItem] = Field(..., description="Registered routing profiles")


class DatabaseDiagnostics(BaseModel):
    """Sanitized database diagnostics."""

    available: bool = Field(..., description="Whether database connection is available")
    degraded: bool = Field(..., description="Whether running in degraded in-memory mode")
    mode: str = Field(
        ..., description="Database operation mode ('wal', 'memory', 'in_memory_fallback', 'none')"
    )
    reason: str | None = Field(
        default=None, description="Sanitized degradation reason if running degraded"
    )
    journal_mode: str | None = Field(
        default=None, description="SQLite journal mode (e.g. 'wal', 'memory', or None)"
    )


class GatewayDiagnosticsResponse(BaseModel):
    """Sanitized diagnostic summary for local gateway administration."""

    status: str = Field(default="ok", description="Overall gateway status")
    database: DatabaseDiagnostics = Field(..., description="Persistence subsystem health")
    registered_providers_count: int = Field(
        ..., description="Total count of registered provider adapters"
    )
    catalog_entries_count: int = Field(..., description="Total models present in catalog")
    stale_models_count: int = Field(
        ..., description="Count of models marked stale awaiting refresh"
    )
    routing_profiles_count: int = Field(
        ..., description="Total count of active routing profiles"
    )
