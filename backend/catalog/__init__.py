"""Model Catalog package for FreeFlow AI.

Manages unified model discovery, metadata normalization, capability queries,
and stale tracking across multiple provider adapters.
"""

from .models import CatalogEntry, CatalogRefreshResult
from .service import ModelCatalog, default_catalog

__all__ = [
    "CatalogEntry",
    "CatalogRefreshResult",
    "ModelCatalog",
    "default_catalog",
]
