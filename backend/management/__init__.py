"""Management API package for FreeFlow AI.

Exposes authenticated management endpoints under /api.
"""

from .routes import management_router

__all__ = ["management_router"]
