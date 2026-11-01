# Backend FastAPI application for FreeFlow AI

import secrets

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings
from .logger import logger

app = FastAPI(title="FreeFlow AI Backend", version="0.1.0")


# Health endpoint (unauthenticated)
@app.get("/health", summary="Health check")
async def health():
    logger.info("Health endpoint called")
    return {"status": "ok"}


# Simple token auth dependency
security = HTTPBearer(auto_error=False)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # noqa: B008
):
    if credentials is None:
        logger.warning("Missing auth credentials")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    scheme, token = credentials.scheme, credentials.credentials
    if scheme.lower() != "bearer":
        logger.warning("Invalid auth scheme", scheme=scheme)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    expected = settings.api_token
    # If token not set, reject all
    if not expected:
        logger.warning("Auth token not configured")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    if not secrets.compare_digest(token, expected):
        logger.warning("Invalid token provided")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return token


# Protected test endpoint
@app.get("/protected", summary="Protected test endpoint")
async def protected(_: str = Depends(verify_token)):
    logger.info("Protected endpoint accessed")
    return {"message": "Authenticated access"}
