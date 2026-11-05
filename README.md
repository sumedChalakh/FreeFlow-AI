# FreeFlow AI

**Last updated:** 2026-11-05T19:55:00+05:30  
**Status:** Phase 9 (Packaging, Distribution, CI/CD & Portfolio Release) verified. 167 tests passing across 13 test modules; Ruff linting, Ruff formatting, and Mypy clean.  
**Working product name:** FreeFlow AI (provisional)

FreeFlow AI is a **local-first, provider-agnostic AI gateway** that unifies local and remote AI models behind a single OpenAI-compatible API, complete with intelligent capability routing, automatic failover, SQLite persistence, and an operator dashboard.

It is designed to give developers, IDEs, and local tools a unified, resilient loopback endpoint without coupling client applications to specific backend providers or model tag formats.

---

## Current Status

| Item | Reality |
|---|---|
| **Milestone** | Phase 9 (Packaging, Distribution, CI/CD & Portfolio Release) verified |
| **Git** | Initialized, branch `main`, remote `origin` configured |
| **Backend** | FastAPI app, health reporting, constant-time Bearer auth, structured redacted logging, SQLite persistence, Model Catalog, Routing Engine, `/v1` endpoints, `/api` management endpoints |
| **Frontend** | Dark-first Operator Dashboard served at `/dashboard` (Overview, Providers, Catalog, Profiles, Diagnostics; HTML/CSS/JS, zero external CDNs) |
| **Packaging & CI** | Production `Dockerfile` (non-root, volume persistence), `.dockerignore`, GitHub Actions multi-OS CI matrix (`ubuntu-latest`, `windows-latest`) |
| **Tests** | 167 passed (`pytest`); Ruff lint clean, Ruff format clean, Mypy clean |
| **License** | **Provisional — pending project owner decision (OQ-001).** Do not assume an open-source license. |

Authoritative live status: [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md).

---

## What FreeFlow AI Solves

- **Provider Fragmentation:** Local models (via Ollama) and external providers format identifiers, capabilities, and errors differently. FreeFlow AI normalizes these into standard OpenAI interfaces.
- **Failover Without Leaks:** When a provider encounters a transient failure (timeout, rate limit, service outage), the routing engine automatically fails over to the next eligible candidate in the active profile—without leaking prompts, credentials, or internal stack traces.
- **Explicit vs. Profile Routing:** Direct deployment requests (e.g. `ollama:llama3.2:latest`) execute with strict non-fallback guarantees, while profile requests (e.g. `coding`, `fast`, `reasoning`) leverage priority-ordered candidate failover.
- **Local-First Privacy:** All credentials and secrets remain strictly on your machine. API tokens are held only in browser memory, and prompt contents are never persisted or forwarded to external telemetry.

---

## High-Level Architecture

```text
  Client Application / IDE / Cursor
                 │
                 ▼  HTTP (Bearer Auth)
  ┌────────────────────────────────────────────────────────┐
  │ Local Gateway API (127.0.0.1:8000)                     │
  │                                                        │
  │   ├── Token Authentication (constant-time check)       │
  │   ├── OpenAI-Compatible Gateway (/v1/models, /v1/chat) │
  │   ├── Management API (/api/providers, /api/catalog)    │
  │   │                                                    │
  │   ├── Intelligent Routing Engine                       │
  │   │     ├── Target & Profile Resolution                │
  │   │     ├── Capability Constraints Filter              │
  │   │     ├── Cooldown & Health Tracker                  │
  │   │     └── Bounded Failover on Retryable Errors       │
  │   │                                                    │
  │   ├── Unified Model Catalog                            │
  │   │     ├── Isolated Discovery per Provider            │
  │   │     ├── Composite ID Disambiguation                │
  │   │     └── Stale State Tracking                       │
  │   │                                                    │
  │   ├── SQLite Storage (WAL mode, transactional refresh) │
  │   │                                                    │
  │   └── Provider Adapters                                │
  │         ├── Local Ollama Adapter                       │
  │         └── Hermetic Mock Adapter                      │
  └────────────────────────────────────────────────────────┘
                 ▲
                 │
  ┌────────────────────────────────────────────────────────┐
  │ Operator Web Dashboard (/dashboard)                    │
  │ Zero-CDN, HTML/CSS/JS, Volatile In-Memory Auth         │
  └────────────────────────────────────────────────────────┘
```

---

## Key Capabilities

### 1. OpenAI-Compatible HTTP API (`/v1`)
- **`GET /v1/models`:** Lists available routing profile aliases (`default`, `coding`, `fast`, `reasoning`) and discovered model deployments in standard OpenAI format without triggering external discovery.
- **`POST /v1/chat/completions`:** Executes chat completions using target model tags or profile aliases. Preserves genuine token usage metadata without fabricating counts.
- **Error Normalization:** Converts provider errors and validation failures into standard OpenAI envelopes (`message`, `type`, `code`, `param`) with zero traceback or sensitive file path leakage.

### 2. Intelligent Routing Engine & Bounded Failover
- **Candidate Sequences:** Profiles specify an ordered list of candidates (`#1 Primary`, `#2 Failover`).
- **Capability Filtering:** Candidates lacking required features (streaming, tool calling, vision) are filtered out automatically before invocation.
- **Cooldown Tracking:** Temporary exclusion of deployments after consecutive retryable failures (`timeout`, `unavailable`, `rate_limit`), automatically recovering when the cooldown expires.
- **Strict Non-Fallback:** Explicit model requests (`provider:model`) never silently fallback to another deployment.

### 3. Unified Model Catalog & SQLite Persistence
- **Composite Disambiguation:** Resolves ambiguous model names into unambiguous composite IDs (`<provider_id>:<model_id>`).
- **Transactional Refresh:** Refreshes models atomically with SQLite rollback on failure, preserving memory consistency.
- **Honest Stale Tracking:** Models restored from SQLite on startup are flagged `is_stale = True` until confirmed active by live discovery.
- **Degraded Mode:** If SQLite is corrupted or unavailable, the gateway automatically falls back to observable in-memory operation (`in_memory_fallback`) while preserving forensic copies of corrupt files.

### 4. Operator Web Dashboard (`/dashboard`)
- **Overview View:** Real-time metrics for gateway status, persistence engine (WAL mode), provider count, catalog count, stale models, and active routing profiles.
- **Provider Management:** Registered adapter details with on-demand connection reachability and latency probing (`POST /api/providers/{id}/test`).
- **Model Catalog Explorer:** Filterable deployment cards with capability badges and on-demand discovery refresh (`POST /api/catalog/refresh`).
- **Routing Profile Explorer:** Priority-ordered failover candidate visualization, retry budgets, timeout ceilings, and capability constraints.
- **Diagnostics Inspector:** Complete subsystem inventory, storage health, and operational warnings.

---

## Getting Started

### Prerequisites
- Python 3.12 or higher
- [`uv`](https://github.com/astral-sh/uv) (fast Python package installer and resolver)
- Local [Ollama](https://ollama.com/) instance (optional, for local model inference)

### Local Native Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url> freeflow-ai
   cd freeflow-ai
   ```

2. **Install dependencies:**
   ```bash
   uv sync --extra dev
   ```

3. **Configure environment:**
   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env

   # Linux / macOS
   cp .env.example .env
   ```
   Set your secret token in `.env`:
   ```env
   FREEFLOW_API_TOKEN=your-secure-random-token
   ```

4. **Run the gateway:**
   ```bash
   uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```

5. **Verify health:**
   ```bash
   curl http://127.0.0.1:8000/health
   ```

6. **Open the Operator Dashboard:**
   Open `http://127.0.0.1:8000/dashboard` in your browser. Enter your `FREEFLOW_API_TOKEN` to authenticate.

---

## Docker Deployment

FreeFlow AI provides a production-conscious, multi-stage `Dockerfile` with non-root execution and volume persistence.

### Persistent Storage & Loopback Mapping
```bash
# 1. Build the container image
docker build -t freeflow-ai:latest .

# 2. Run with volume persistence and loopback publishing
docker run -d \
  --name freeflow-ai \
  -p 127.0.0.1:8000:8000 \
  -v freeflow-data:/data \
  -e FREEFLOW_API_TOKEN="your-secure-random-token" \
  -e FREEFLOW_OLLAMA_BASE_URL="http://host.docker.internal:11434" \
  --restart unless-stopped \
  freeflow-ai:latest
```

> [!IMPORTANT]
> Always publish to host loopback (`-p 127.0.0.1:8000:8000`), never `-p 8000:8000`, to preserve local-first network security.

Detailed operational instructions, Linux host gateway configuration, and Docker Compose files: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## API Usage Examples

### 1. List Available Models & Routing Profiles
```bash
curl -X GET http://127.0.0.1:8000/v1/models \
  -H "Authorization: Bearer your-secure-random-token"
```

### 2. Create a Chat Completion via Profile
```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer your-secure-random-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "coding",
    "messages": [
      {"role": "system", "content": "You are a concise programming assistant."},
      {"role": "user", "content": "Write a Python function to check for prime numbers."}
    ],
    "temperature": 0.2
  }'
```

### 3. Create a Chat Completion via Explicit Deployment
```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer your-secure-random-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama:llama3.2:latest",
    "messages": [
      {"role": "user", "content": "Explain WAL mode in SQLite in two sentences."}
    ]
  }'
```

---

## Verification & Quality Gates

Run all automated tests, linters, and type-checkers via `uv`:

```bash
# Run 167 automated unit and integration tests
uv run pytest -v

# Run Ruff code analysis
uv run ruff check .

# Run Ruff format check
uv run ruff format --check .

# Run Mypy static type verification across all source files
uv run mypy .
```

### Continuous Integration
Automated testing is configured via GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) testing across a multi-OS matrix (`ubuntu-latest` and `windows-latest`) on Python 3.12 with dependency caching and least-privilege permissions.

---

## Verified Limitations

- **Streaming Unsupported:** Token streaming (`stream=True`) is explicitly rejected with HTTP 400.
- **Hosted Providers Pending:** Hosted vendor integrations (OpenRouter, Anthropic, Groq) are planned for Phase 3 upon resolution of license selection (`OQ-001`), hosted vendor selection (`OQ-004`), and Windows credential storage (`OQ-005`).
- **Read-Only Profiles:** Routing profile editing via dashboard is planned for a future release; profiles are currently configured via code or startup restoration.

---

## Documentation Index

- [`AGENTS.md`](AGENTS.md) — Mandatory protocol for AI agents and contributors.
- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — Live milestone progress and verification records.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — Production operations, Docker, and backup recovery.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — System design and request lifecycle.
- [`docs/SECURITY_AND_PRIVACY.md`](docs/SECURITY_AND_PRIVACY.md) — Threat model and security controls.
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — Chronological history of technical changes.
- [`docs/SESSION_LOG.md`](docs/SESSION_LOG.md) — Append-only engineering session audit logs.
- [`docs/RISKS_AND_OPEN_QUESTIONS.md`](docs/RISKS_AND_OPEN_QUESTIONS.md) — Active risk and decision tracker.

---

## Licensing Notice

**Status: Provisional — License Pending (OQ-001).**  
No open-source license has been selected or applied. All rights are reserved by the project owner. Do not copy, distribute, or assume an open-source license until an official license file is approved and committed by the owner.
