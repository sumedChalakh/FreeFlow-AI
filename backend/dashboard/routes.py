"""FastAPI routes for the FreeFlow AI Web Dashboard.

Provides routes for serving the HTML application shell and redirecting root requests.
Does not duplicate backend business logic or bypass existing authentication mechanisms.
"""

from pathlib import Path

from fastapi import APIRouter, status
from fastapi.responses import HTMLResponse, RedirectResponse

dashboard_router = APIRouter(tags=["Dashboard"])

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"


@dashboard_router.get(
    "/dashboard",
    response_class=HTMLResponse,
    summary="Dashboard application shell and overview",
)
async def get_dashboard() -> HTMLResponse:
    """Serve the FreeFlow AI web dashboard application shell."""
    index_path = TEMPLATES_DIR / "dashboard.html"
    if not index_path.is_file():
        return HTMLResponse(
            content="<h1>FreeFlow AI: Dashboard template not found</h1>",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    content = index_path.read_text(encoding="utf-8")
    return HTMLResponse(content=content, status_code=status.HTTP_200_OK)


@dashboard_router.get("/", summary="Root redirect", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    """Redirect root path requests to the main dashboard interface."""
    return RedirectResponse(
        url="/dashboard",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
