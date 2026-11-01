"""FastAPI dependencies for FreeFlow AI API endpoints.

Provides consistent dependency injection for configuration, authentication,
the ModelCatalog, and the RoutingEngine.
"""

import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.catalog.service import ModelCatalog, default_catalog
from backend.config import settings
from backend.db import DatabaseManager
from backend.logger import logger
from backend.providers.registry import ProviderRegistry
from backend.providers.registry import registry as default_registry
from backend.routing.engine import RoutingEngine, default_engine

security = HTTPBearer(auto_error=False)


def get_catalog(request: Request) -> ModelCatalog:
    """Provide the ModelCatalog instance from app state if set, else default."""
    cat = getattr(request.app.state, "catalog", None)
    if isinstance(cat, ModelCatalog):
        return cat
    return default_catalog


def get_routing_engine(request: Request) -> RoutingEngine:
    """Provide the RoutingEngine instance from app state if set, else default."""
    engine = getattr(request.app.state, "routing_engine", None)
    if isinstance(engine, RoutingEngine):
        return engine
    return default_engine


def get_provider_registry(request: Request) -> ProviderRegistry:
    """Provide the ProviderRegistry instance from app state or catalog if set, else default."""
    reg = getattr(request.app.state, "registry", None)
    if isinstance(reg, ProviderRegistry):
        return reg
    cat = getattr(request.app.state, "catalog", None)
    if isinstance(cat, ModelCatalog) and hasattr(cat, "_registry"):
        return cat._registry
    return default_registry


def get_db_manager(request: Request) -> DatabaseManager | None:
    """Provide the active DatabaseManager instance from app state, if initialized."""
    mgr = getattr(request.app.state, "db_manager", None)
    if isinstance(mgr, DatabaseManager):
        return mgr
    return None


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # noqa: B008
) -> str:
    """Authenticate incoming requests using the configured FREEFLOW_API_TOKEN.

    Rejects missing, malformed, or invalid tokens with HTTP 401.
    """
    if credentials is None:
        logger.warning("Missing auth credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing Bearer token",
        )
    scheme, token = credentials.scheme, credentials.credentials
    if scheme.lower() != "bearer":
        logger.warning("Invalid auth scheme", scheme=scheme)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid auth scheme",
        )
    import backend.main as main_mod

    expected = getattr(main_mod, "settings", settings).api_token
    if not expected:
        logger.warning("Auth token not configured")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: API token not configured on server",
        )
    if not secrets.compare_digest(token, expected):
        logger.warning("Invalid token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid token",
        )
    return token
