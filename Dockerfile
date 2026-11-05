# ==============================================================================
# FreeFlow AI — Production-Conscious Dockerfile
# Multi-stage container build with non-root security and SQLite volume persistence.
# ==============================================================================

FROM python:3.12-slim-bookworm

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Install uv from official binary image
COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /uvx /bin/

# Create non-root system user and dedicated directories
RUN groupadd -r -g 1000 freeflow && \
    useradd -r -u 1000 -g freeflow -d /app -s /sbin/nologin freeflow && \
    mkdir -p /app /data && \
    chown -R freeflow:freeflow /app /data

WORKDIR /app

# Copy dependency specifications first for layer caching
COPY --chown=freeflow:freeflow pyproject.toml uv.lock ./

# Install runtime dependencies only (excluding dev/test packages)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source code and assets
COPY --chown=freeflow:freeflow backend/ ./backend/
COPY --chown=freeflow:freeflow README.md ./

# Install the project itself in the uv virtual environment
RUN uv sync --frozen --no-dev

# Switch to non-root user
USER freeflow

# Runtime environment defaults
# Note: Container binds 0.0.0.0 internally to accept published traffic from Docker engine.
# Operators MUST publish to host loopback only (-p 127.0.0.1:8000:8000) for security.
ENV FREEFLOW_API_HOST=0.0.0.0 \
    FREEFLOW_API_PORT=8000 \
    FREEFLOW_DB_PATH=/data/freeflow.db \
    FREEFLOW_LOG_LEVEL=INFO \
    FREEFLOW_OLLAMA_BASE_URL=http://host.docker.internal:11434

# Declare persistence volume for SQLite database
VOLUME ["/data"]

EXPOSE 8000

# Container healthcheck using existing GET /health endpoint (no extra tools needed)
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).getcode() == 200 else 1)"

# Start FastAPI gateway via uvicorn
ENTRYPOINT ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
