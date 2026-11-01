"""Registry for FreeFlow AI provider adapters.

Decouples provider lifecycle management from routing logic, avoiding
hardcoded provider branching throughout the codebase.
"""

from .base import ProviderAdapter


class ProviderRegistry:
    """Registry maintaining active provider adapter instances."""

    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    def register(self, adapter: ProviderAdapter) -> None:
        """Register a provider adapter instance."""
        self._adapters[adapter.adapter_id] = adapter

    def unregister(self, adapter_id: str) -> ProviderAdapter | None:
        """Remove and return an adapter by its ID, if present."""
        return self._adapters.pop(adapter_id, None)

    def get(self, adapter_id: str) -> ProviderAdapter | None:
        """Retrieve an adapter by its ID."""
        return self._adapters.get(adapter_id)

    def require(self, adapter_id: str) -> ProviderAdapter:
        """Retrieve an adapter by ID or raise KeyError if not registered."""
        if adapter_id not in self._adapters:
            raise KeyError(f"Provider adapter {adapter_id!r} is not registered.")
        return self._adapters[adapter_id]

    def list_adapters(self) -> list[str]:
        """Return all registered adapter IDs."""
        return sorted(self._adapters.keys())

    def clear(self) -> None:
        """Clear all registered adapters."""
        self._adapters.clear()


# Module-level default registry instance
registry = ProviderRegistry()
