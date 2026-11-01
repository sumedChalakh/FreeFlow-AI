"""Backend FastAPI application for FreeFlow AI.

Exposes gateway health, authentication verification, and OpenAI-compatible v1 endpoints.
Manages database initialization, catalog restoration, and honest degraded mode reporting.
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from backend.api import register_error_handlers, v1_router
from backend.api.deps import verify_token
from backend.catalog.service import default_catalog
from backend.config import settings
from backend.db import CatalogRepository, DatabaseManager
from backend.logger import logger
from backend.management import management_router
from backend.providers.registry import registry as default_registry
from backend.routing.engine import default_engine

__all__ = ["app", "settings", "verify_token"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup, database initialization, catalog restoration, and shutdown."""
    # 1. Initialize SQLite DatabaseManager (explicit on startup, not in constructor)
    db_mgr = DatabaseManager(db_path=settings.db_path)
    db_mgr.initialize()
    app.state.db_manager = db_mgr

    catalog_repo = CatalogRepository(db_mgr)
    app.state.catalog_repo = catalog_repo

    # 2. Register default local Ollama adapter if needed (zero network calls on init)
    if default_registry.get("ollama") is None:
        from backend.providers.ollama import OllamaAdapter

        default_registry.register(OllamaAdapter(adapter_id="ollama"))

    # 3. Restore persisted provider configurations without credentials
    try:
        saved_providers = await db_mgr.run_in_thread(catalog_repo.load_all_providers)
        for prov in saved_providers:
            prov_id = prov["id"]
            base_url = prov.get("base_url")
            ctx = default_catalog.get_provider_context(prov_id)
            if base_url:
                ctx.base_url = base_url
            default_catalog.set_provider_context(prov_id, ctx)
        if saved_providers:
            logger.info("Startup restored provider configurations", count=len(saved_providers))
    except Exception as exc:
        logger.warning("Failed to restore provider configurations from database", error=str(exc))

    # 4. Attach repository to default catalog and restore stored entries as stale
    default_catalog.set_repository(catalog_repo)
    try:
        restored_count = await default_catalog.restore_from_repository()
        logger.info("Startup restored catalog entries", count=restored_count)
    except Exception as exc:
        logger.warning("Failed to restore catalog entries from database", error=str(exc))

    # 5. Restore customized routing profiles without losing built-in profiles
    try:
        saved_profiles = await db_mgr.run_in_thread(catalog_repo.load_all_profiles)
        for prof in saved_profiles:
            default_engine.register_profile(prof)
        if saved_profiles:
            logger.info("Startup restored custom routing profiles", count=len(saved_profiles))
    except Exception as exc:
        logger.warning("Failed to restore routing profiles from database", error=str(exc))

    yield

    # Shutdown: clean up database connections
    db_mgr.close()


app = FastAPI(title="FreeFlow AI Backend", version="0.1.0", lifespan=lifespan)

# Register normalized error handlers for predictable OpenAI-compatible error bodies
register_error_handlers(app)

# Mount OpenAI-compatible v1 router
app.include_router(v1_router)

# Mount authenticated Management API router
app.include_router(management_router)


# Health endpoint (unauthenticated)
@app.get("/health", summary="Health check")
async def health():
    logger.info("Health endpoint called")
    db_mgr = getattr(app.state, "db_manager", None)
    db_status = (
        db_mgr.get_health_status()
        if db_mgr
        else {"available": False, "degraded": True, "mode": "none"}
    )
    return {
        "status": "ok",
        "database": db_status,
    }


# Protected test endpoint (Phase 1 legacy compatibility)
@app.get("/protected", summary="Protected test endpoint")
async def protected(_: str = Depends(verify_token)):  # noqa: B008
    logger.info("Protected endpoint accessed")
    return {"message": "Authenticated access"}
