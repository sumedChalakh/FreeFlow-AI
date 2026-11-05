# Deployment & Operations Guide

**Last updated:** 2026-11-05T19:55:00+05:30  
**Status:** Complete local and containerized operational guide for FreeFlow AI.

---

## 1. Deployment Philosophy

FreeFlow AI is designed from the ground up as a **local-first, single-operator gateway**. It is intended to run directly on the operator's machine or on an isolated local server, exposing an OpenAI-compatible interface to local IDEs, developer tools, and client scripts.

### Security Non-Negotiables
1. **Loopback Binding by Default:** The gateway defaults to `127.0.0.1`. Never expose FreeFlow AI to `0.0.0.0` or a public interface without a reverse proxy terminating TLS and enforcing strong authentication.
2. **Volatile Token Memory:** The Web Dashboard holds the `FREEFLOW_API_TOKEN` strictly in browser execution memory closure; it is never persisted to disk, `localStorage`, `sessionStorage`, or cookies.
3. **Zero Credential Persistence:** Secrets and API keys are environment-only; they are never stored in SQLite tables or logged in unredacted telemetry.

---

## 2. Native Deployment (Windows, Linux, macOS)

### Prerequisites
- Python 3.12 or higher.
- `uv` (recommended package manager) or standard `pip` + `venv`.
- Local Ollama installation (optional, for local inference).

### Step-by-Step Setup
1. **Clone and Install:**
   ```bash
   git clone <repo-url> freeflow-ai
   cd freeflow-ai
   uv sync
   ```
2. **Configure Environment:**
   Copy the example environment configuration:
   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env

   # Linux / macOS
   cp .env.example .env
   ```
   Generate a secure random token and update `.env`:
   ```env
   FREEFLOW_API_HOST=127.0.0.1
   FREEFLOW_API_PORT=8000
   FREEFLOW_API_TOKEN=your-generated-random-token
   FREEFLOW_DB_PATH=freeflow.db
   FREEFLOW_LOG_LEVEL=INFO
   FREEFLOW_OLLAMA_BASE_URL=http://127.0.0.1:11434
   ```
3. **Launch the Gateway:**
   ```bash
   uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```
4. **Access Endpoints:**
   - Health check: `http://127.0.0.1:8000/health`
   - Operator Dashboard: `http://127.0.0.1:8000/dashboard`
   - OpenAI API: `http://127.0.0.1:8000/v1/chat/completions`

---

## 3. Containerized Deployment (Docker)

FreeFlow AI includes a production-conscious, multi-stage `Dockerfile` based on `python:3.12-slim-bookworm` running as a non-root user (`freeflow`, UID 1000).

### Persistent Storage Strategy
SQLite operates in WAL mode (`journal_mode = WAL`) and requires durable storage across container restarts and recreations. A dedicated volume must be mounted at `/data`.

```text
Host System                     Container Environment (/app)
┌──────────────────────┐        ┌──────────────────────────────┐
│ Docker Volume        │        │ SQLite Database              │
│ (freeflow-data)      │◄──────►│ /data/freeflow.db            │
└──────────────────────┘        └──────────────────────────────┘
```

### Networking & Ollama Host Connectivity
Inside the container, uvicorn binds to `0.0.0.0:8000` to receive forwarded traffic from the Docker bridge. However, the host port mapping **must publish strictly to 127.0.0.1** to preserve the local-first security boundary.

| Host Platform | Ollama Connectivity Setting | Run Flag |
|---|---|---|
| **Docker Desktop (Windows / macOS)** | `FREEFLOW_OLLAMA_BASE_URL=http://host.docker.internal:11434` | Default |
| **Linux (Docker Engine)** | `FREEFLOW_OLLAMA_BASE_URL=http://host.docker.internal:11434` | `--add-host=host.docker.internal:host-gateway` |

### Running with Docker CLI
```bash
# 1. Build the container image
docker build -t freeflow-ai:latest .

# 2. Run with volume persistence and loopback publishing
docker run -d \
  --name freeflow-ai \
  -p 127.0.0.1:8000:8000 \
  -v freeflow-data:/data \
  -e FREEFLOW_API_TOKEN="your-secret-token" \
  -e FREEFLOW_OLLAMA_BASE_URL="http://host.docker.internal:11434" \
  --restart unless-stopped \
  freeflow-ai:latest
```

### Running with Docker Compose
Create a `docker-compose.yml` file:
```yaml
version: '3.8'

services:
  gateway:
    build: .
    image: freeflow-ai:latest
    container_name: freeflow-gateway
    restart: unless-stopped
    ports:
      # Publish only to host loopback interface
      - "127.0.0.1:8000:8000"
    environment:
      - FREEFLOW_API_TOKEN=your-secure-token-here
      - FREEFLOW_DB_PATH=/data/freeflow.db
      - FREEFLOW_OLLAMA_BASE_URL=http://host.docker.internal:11434
      - FREEFLOW_LOG_LEVEL=INFO
    volumes:
      - freeflow-data:/data
    extra_hosts:
      # Required on Linux to reach host Ollama daemon
      - "host.docker.internal:host-gateway"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).getcode() == 200 else 1)"]
      interval: 15s
      timeout: 3s
      retries: 3
      start_period: 5s

volumes:
  freeflow-data:
    name: freeflow-data
```

---

## 4. Backup & Disaster Recovery

### Database Backup
Because FreeFlow AI uses SQLite in WAL mode:
1. **Live Backup (Standard):** Copy `freeflow.db` while the gateway is stopped, or run a query with `VACUUM INTO 'backup.db'`.
2. **Docker Volume Backup:**
   ```bash
   docker run --rm \
     -v freeflow-data:/data:ro \
     -v $(pwd):/backup \
     alpine cp /data/freeflow.db /backup/freeflow.db.bak
   ```

### Forensic Corruption Recovery
If SQLite encounters corruption during startup:
- `DatabaseManager` detects corruption via `PRAGMA quick_check`.
- It preserves the corrupted file as `freeflow.corrupt.<timestamp>_<counter>.db`.
- It automatically activates **honest degraded in-memory mode** (`in_memory_fallback`), logging the diagnostic alert and reporting it via `GET /health` and `GET /api/diagnostics`.
