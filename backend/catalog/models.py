"""Data models for FreeFlow AI unified Model Catalog.

Provides normalized representations of cataloged model deployments,
tracking capabilities, locality, freshness, and refresh diagnostic results.
"""

import time

from pydantic import BaseModel, Field

from backend.providers.base import ModelCapability, ProviderModel


class CatalogEntry(BaseModel):
    """A distinct model deployment listed in the unified catalog.

    Uniquely identified by the combination of provider_id and model_id
    (e.g., 'ollama:llama3.2:latest' vs 'mock:llama3.2:latest').
    """

    composite_id: str = Field(
        ...,
        description="Unambiguous identifier formatted as '<provider_id>:<model_id>'",
    )
    provider_id: str = Field(..., description="ID of the provider offering this model")
    model_id: str = Field(..., description="Provider-specific model identifier")
    display_name: str = Field(..., description="Human-readable display name")
    capabilities: ModelCapability = Field(
        default_factory=ModelCapability,
        description="Normalized model capabilities",
    )
    is_local: bool = Field(
        default=False,
        description="True if hosted on local hardware (e.g. Ollama)",
    )
    is_stale: bool = Field(
        default=False,
        description="True if provider discovery failed or model was omitted in latest refresh",
    )
    last_seen_at: float | None = Field(
        default=None,
        description="Unix timestamp when model was last successfully returned by provider",
    )
    last_checked_at: float | None = Field(
        default=None,
        description="Unix timestamp of the most recent refresh attempt for this model",
    )

    @classmethod
    def from_provider_model(
        cls,
        model: ProviderModel,
        *,
        checked_at: float | None = None,
        seen_at: float | None = None,
        is_stale: bool = False,
    ) -> "CatalogEntry":
        """Construct a CatalogEntry from a ProviderModel."""
        now = time.time()
        c_at = checked_at if checked_at is not None else now
        s_at = seen_at if seen_at is not None else now
        return cls(
            composite_id=f"{model.provider_id}:{model.id}",
            provider_id=model.provider_id,
            model_id=model.id,
            display_name=model.display_name,
            capabilities=model.capabilities,
            is_local=model.is_local,
            is_stale=is_stale,
            last_seen_at=s_at,
            last_checked_at=c_at,
        )


class CatalogRefreshResult(BaseModel):
    """Outcome of refreshing model inventory from a single provider."""

    provider_id: str = Field(..., description="Provider that was refreshed")
    success: bool = Field(..., description="Whether discovery succeeded")
    models_count: int = Field(
        default=0,
        ge=0,
        description="Number of active models discovered from this provider",
    )
    error: str | None = Field(
        default=None,
        description="Error details if discovery failed, or None on success",
    )
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp when refresh completed",
    )
