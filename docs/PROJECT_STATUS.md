# Project status

**Last updated:** 2026-11-01T00:23:00+05:30  
**Current milestone:** Persistence Audit & Phase 7 Preparation (verified; 105 tests passing)  
**Latest session log:** [`SESSION_LOG.md`](SESSION_LOG.md) entry `2026-11-01T00:23:00+05:30`

---

## Snapshot

| Field | Value |
|---|---|
| Product name | FreeFlow AI (provisional) |
| Application code | Backend API (`backend/api/`, `backend/main.py`), Routing (`backend/routing/`), Catalog (`backend/catalog/`), Persistence (`backend/db/`), Providers (`backend/providers/`) |
| Git | Initialized, branch `main`, remote `origin` configured |
| Tests | 105 passed (`pytest`); ruff, mypy clean |
| License | Unchosen |
| Blockers | Open questions OQ-001 (license), OQ-004 (hosted providers), OQ-005 (credential storage) |

---

## Implemented and verified

- Repository audit completed (directory listing + Git probe).
- Documentation system created: `AGENTS.md`, `README.md`, `.gitignore`, `.env.example`, and the `docs/` tree including ADR-0001.
- Documentation-first workflow written so future agents must read docs before coding and log meaningful changes with Asia/Kolkata timestamps.
- Git repository initialized on branch `main`, remote `origin` configured to GitHub.
- **Backend skeleton (P1-T1):** `backend/__init__.py`, `main.py`, `config.py`, `logger.py`. FastAPI app starts via `uvicorn backend.main:app`.
- **Health endpoint (P1-T2):** `GET /health` returns `{"status": "ok", "database": {...}}` (200). Unauthenticated. Transparently reports SQLite availability and degraded mode status.
- **Local API authentication (P1-T3):** Bearer token auth via `FREEFLOW_API_TOKEN` env var. Unauthenticated requests to protected endpoints return 401.
- **Structured, redacted logging (P1-T4):** `structlog`-based logger with `SecretRedactor` processor. Fields named `token`, `api_token`, `password`, `secret`, `key` are redacted.
- **Quality tooling (P1-T5):** `pyproject.toml` declares `pytest`, `httpx`, `ruff`, `mypy` as dev dependencies with tool configuration sections. `uv sync --extra dev` installs them.
- **Configuration:** `pydantic-settings` `BaseSettings` with `FREEFLOW_` env prefix, `.env` file support, `FREEFLOW_DB_PATH` setting, loopback default.
- **Provider adapter interface (P2-T1):** Abstract protocol `ProviderAdapter` with typed models (`ChatMessage`, `ChatCompletionRequest`, `ChatCompletionResponse`, `UsageInfo`, `ModelCapability`, `ProviderModel`, `ConnectionHealth`, `ProviderContext`).
- **Normalized error hierarchy (P2-T4):** `ErrorCategory` enum and `ProviderError` hierarchy with `is_retryable` property, supporting `auth`, `permission`, `invalid_request`, `context_length`, `rate_limit`, `timeout`, `unavailable`, `malformed_response`, and `unsupported`.
- **Mock provider adapter (P2-T2):** `MockProviderAdapter` with deterministic responses, simulation of timeout/unavailable/rate-limit/malformed/auth errors, model discovery, and honest unknown usage tracking.
- **Ollama local provider adapter (P2-T3):** `OllamaAdapter` with model discovery (`GET /api/tags`), health probe (`GET /`), and non-streaming chat completions (`POST /api/chat`). Full mapping of HTTP/transport errors to `ProviderError` taxonomy.
- **Capability metadata normalization (P2-T5):** `detect_ollama_capabilities` normalizes streaming (`True`), vision, and tool calling without claiming unsupported capabilities. Preserves unknown context windows as `None` (unknown, not zero).
- **Provider registry:** `ProviderRegistry` for decoupled adapter registration and lookup without hardcoded vendor branching.
- **Unified Model Catalog (`backend/catalog/`):** `ModelCatalog` and `CatalogEntry` with unambiguous composite IDs (`<provider_id>:<model_id>`), isolated provider discovery, concurrency-safe locking (`asyncio.Lock`) and snapshotting, stale retention on refresh failures, model departure detection, empty model list handling, deduplication, capability/locality filtering, and SQLite repository binding.
- **Routing Engine & Automatic Failover (`backend/routing/`):**
  - Colon-safe model resolution (`ModelResolver`) preserving raw model tags (`ollama:llama3.2:3b`).
  - Strict explicit routing: explicit deployment requests (`provider:model`) never silently fallback.
  - Routing profiles (`default`, `coding`, `fast`, `reasoning`) with priority-ordered candidate selection and `list_profiles()` introspection.
  - Capability constraints: automatically filters candidates that do not meet request requirements (streaming, tools, vision).
  - Health tracking and configurable cooldown (`CooldownTracker`) with temporary exclusion after consecutive failures.
  - Bounded retry budget and failover only on retryable errors (`timeout`, `unavailable`, `rate_limit`). Non-retryable errors (`auth`, `invalid_request`) abort immediately.
  - Structured routing telemetry (`RoutingDecisionEvent`) without logging prompt or message contents.
- **OpenAI-Compatible Gateway API (`backend/api/`):**
  - `GET /v1/models` (P6-T1): Lists available routing profile aliases (including restored custom profiles) and active catalog deployments in standard OpenAI list format without contacting external providers.
  - `POST /v1/chat/completions` (P6-T2): Executes non-streaming completions via `RoutingEngine`. Preserves honest token usage metadata.
  - Error normalization (P6-T3): Custom exception handlers map `ProviderError`, `HTTPException`, and `RequestValidationError` into OpenAI envelope shapes (`error.message`, `error.type`, `error.code`, `error.param`). Zero leakage of prompts, secrets, or internal stack traces.
  - Streaming disclosure (P6-T4): `stream=True` is explicitly rejected with HTTP 400 without false claims.
  - Dependency injection: `backend/api/deps.py` provides clean injection for `ModelCatalog`, `RoutingEngine`, and `verify_token`.
- **SQLite Persistence & Startup Restoration (P4-T1):**
  - Standard-library `sqlite3` implementation in `backend/db/` (`DatabaseManager`, `CatalogRepository`, `run_migrations`).
  - `PRAGMA user_version = 1` sequential, transactional migration runner. Tables: `providers`, `catalog_models`, `routing_profiles`.
  - Performance & safety pragmas: WAL mode (`PRAGMA journal_mode = WAL`), foreign keys, busy timeout (`5000ms`), thread synchronization via `threading.RLock` ensuring safe execution across worker thread dispatches and direct callers.
  - Lifespan initialization and restoration: models restored marked `is_stale = True` until refreshed; custom routing profiles rehydrated into `RoutingEngine`; non-secret provider configurations loaded without credentials.
  - Transactional provider refreshes: atomic replacement of active models, mark omitted models as stale, transaction rollback on failure preserving in-memory consistency.
  - Forensic corruption handling: corrupt database files preserved as `<name>.corrupt.<timestamp_ms>_<counter>.db` with millisecond collision resistance before in-memory fallback.
  - Honest degraded mode: health endpoint reports degraded status, reason, and mode (`wal`, `memory`, `in_memory_fallback`, `none`).
  - Strict privacy: zero credentials, API keys, bearer tokens, prompts, or message payloads persisted.
- **Tests:** 105 tests across 9 files (API v1, persistence, health, auth, logging/redaction, mock provider, ollama adapter, model catalog, routing engine). All pass deterministically without external dependencies or internet access.

Verified by: `uv run pytest -v` (105 passed in 0.74s); `uv run ruff check .` (all passed); `uv run ruff format --check .` (157 files formatted); `uv run mypy .` (0 issues, 37 files). Run on 2026-11-01T00:23+05:30.

---

## Partially implemented

- None. Phase 1, Phase 2, Phase 4 (including P4-T1), Phase 5, and Phase 6 are fully implemented and verified.

---

## Not started

- Hosted provider integrations (Phase 3).
- Web Dashboard (Phase 7).
- Reliability, security hardening, and usability polish (Phase 8).
- Packaging and portfolio release (Phase 9).
- Web dashboard (Phase 7).
- Packaging, Docker, and portfolio release (Phase 9).
- LICENSE.

---

## Current blockers

1. Material open questions: OQ-001 license, OQ-005 credential storage — do not silently decide.
2. OQ-004 hosted providers: owner must choose first hosted vendors before Phase 3 implementation.
3. OQ-003 frontend stack: proposed but not confirmed; Phase 7 can decide.

---

## Latest test status

**Run on 2026-10-31T22:30:27+05:30:**

| Tool | Command | Result |
|---|---|---|
| pytest | `uv run pytest -v` | 68 passed in 0.54s (exit 0) |
| ruff lint | `uv run ruff check .` | All checks passed (exit 0) |
| ruff format | `uv run ruff format --check .` | 140 files already formatted (exit 0) |
| mypy | `uv run mypy .` | Success: no issues found in 20 source files (exit 0) |

---

## Risks needing attention

- R-001/R-002: catalog honesty once providers exist.
- R-003: do not persist plaintext keys if Phase 3 starts before OQ-005 is decided.

Full list: [`RISKS_AND_OPEN_QUESTIONS.md`](RISKS_AND_OPEN_QUESTIONS.md).

---

## Next 1–3 recommended tasks

1. Resolve OQ-004 (select first hosted providers from official docs + available credentials) for Phase 3.
2. Implement Phase 4 SQLite catalog persistence (`P4-T1`).
3. Commit verified Phase 1, Phase 2, and Model Catalog milestone changes.

---

## Consistency notes

- Backend health endpoint, auth, mock provider, Ollama adapter, and in-memory Model Catalog are implemented and tested.
- Planned APIs beyond `/health` and `/protected` remain labeled proposed in their canonical docs.
- Original plan file is preserved and is not live status.
- Hosted adapters, SQLite catalog tables, routing engine, and dashboard do not exist yet.
