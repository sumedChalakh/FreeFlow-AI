# Project status

**Last updated:** 2026-11-05T19:45:00+05:30  
**Current milestone:** Phase 8: Reliability, Security Hardening & Usability Audit (verified; 161 tests passing)  
**Latest session log:** [`SESSION_LOG.md`](SESSION_LOG.md) entry `2026-11-05T19:45:00+05:30`

---

## Snapshot

| Field | Value |
|---|---|
| Product name | FreeFlow AI (provisional) |
| Application code | Backend API (`backend/api/`, `backend/management/`, `backend/dashboard/`, `backend/main.py`), Routing (`backend/routing/`), Catalog (`backend/catalog/`), Persistence (`backend/db/`), Providers (`backend/providers/`) |
| Git | Initialized, branch `main`, remote `origin` configured |
| Tests | 161 passed (`pytest`); ruff, mypy clean |
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
  - Dependency injection: `backend/api/deps.py` provides clean injection for `ModelCatalog`, `RoutingEngine`, `verify_token`, `ProviderRegistry`, and `DatabaseManager`.
- **SQLite Persistence & Startup Restoration (P4-T1):**
  - Standard-library `sqlite3` implementation in `backend/db/` (`DatabaseManager`, `CatalogRepository`, `run_migrations`).
  - `PRAGMA user_version = 1` sequential, transactional migration runner. Tables: `providers`, `catalog_models`, `routing_profiles`.
  - Performance & safety pragmas: WAL mode (`PRAGMA journal_mode = WAL`), foreign keys, busy timeout (`5000ms`), thread synchronization via `threading.RLock` ensuring safe execution across worker thread dispatches and direct callers.
  - Lifespan initialization and restoration: models restored marked `is_stale = True` until refreshed; custom routing profiles rehydrated into `RoutingEngine`; non-secret provider configurations loaded without credentials.
  - Transactional provider refreshes: atomic replacement of active models, mark omitted models as stale, transaction rollback on failure preserving in-memory consistency.
  - Forensic corruption handling: corrupt database files preserved as `<name>.corrupt.<timestamp_ms>_<counter>.db` with millisecond collision resistance before in-memory fallback.
  - Honest degraded mode: health endpoint reports degraded status, reason, and mode (`wal`, `memory`, `in_memory_fallback`, `none`).
  - Strict privacy: zero credentials, API keys, bearer tokens, prompts, or message payloads persisted.
- **Authenticated Management API (Phase 7, Milestone P7-M1):**
  - `GET /api/providers`: Returns registered adapters, base URLs, locality, and credential presence without leaking secrets.
  - `POST /api/providers/{provider_id}/test`: Executes non-destructive health and latency probe (`test_connection(ctx)`), returning sanitized errors.
  - `GET /api/catalog`: Returns active and stale catalog models with provider filtering and capability flags.
  - `POST /api/catalog/refresh`: Initiates concurrency-safe live discovery for all or single provider with SQLite synchronization.
  - `GET /api/profiles`: Lists built-in and dynamic routing profiles with candidate order and retry configurations.
  - `GET /api/diagnostics`: Reports gateway operational status, persistence mode (WAL vs. degraded), and catalog/profile counts with file path and token sanitization.
- **Web Dashboard App Shell & Overview (Phase 7, Milestone P7-M2):**
  - `GET /dashboard`: Responsive, dark-first HTML application shell served via FastAPI with semantic sidebar navigation, top header, status pills, refresh controls, and overview metrics cards.
  - `GET /`: Clean HTTP 307 redirect to `/dashboard`.
  - Static asset delivery: `/dashboard/static/dashboard.css` and `/dashboard/static/dashboard.js` with zero external CDN dependencies.
  - Secure in-memory token authentication: `FREEFLOW_API_TOKEN` is held strictly in volatile page memory, never saved to `localStorage`, `sessionStorage`, cookies, query parameters, or disk.
  - Genuine API data rendering: Gateway status, SQLite WAL/degraded persistence health, provider counts, catalog counts, stale model counts, and active routing profiles are populated directly from `GET /api/diagnostics` and `GET /api/providers`.
- **Provider Management & Live Probe Interface (Phase 7, Milestone P7-M3):**
  - Functional sidebar navigation between Overview (`#overview`) and Providers (`#providers`) with accessible semantics (`aria-current="page"`).
  - Dedicated Provider Management view (`#providers-view`) rendering detailed cards for all registered providers (display name, id, locality badge, endpoint URL, credential presence, enabled status).
  - Explicit on-demand connection testing (`POST /api/providers/{provider_id}/test`) with per-provider duplicate click prevention, loading state, latency reporting, and sanitized error display.
  - Strictly prevents implicit background probing on view load, navigation, or provider list refresh.
  - Per-provider in-memory probe result caching during the session.
  - XSS-safe DOM creation avoiding `innerHTML` interpolation of provider attributes.
- **Model Catalog Explorer & On-Demand Discovery Refresh (Phase 7, Milestone P7-M4):**
  - Activated Model Catalog in navigation with responsive hash routing (`#catalog`).
  - Dedicated Model Catalog view panel (`#catalog-view`) with cards layout, metadata tags, and capability badges.
  - Displays composite IDs (`<provider_id>:<model_id>`), provider ownership, locality classification (`Local` vs. `Hosted`), context window tokens, and last seen timestamps.
  - Honest Stale Model Presentation: models restored from SQLite are highlighted with distinct `Stale` badges and warning callouts explaining that live availability is unverified.
  - Client-side provider filtering dropdown without triggering implicit discovery requests.
  - Explicit on-demand discovery refresh (`POST /api/catalog/refresh`) supporting complete discovery, partial discovery reporting with sanitized provider error messages, duplicate click prevention, in-flight loading spinners, and automatic catalog re-fetching.
  - Zero token or secret leakage; DOM manipulation strictly uses `document.createElement` and `textContent`.
- **Routing Profile Explorer & Diagnostics Inspector (Phase 7, Milestone P7-M5):**
  - Activated Routing Profiles (`#profiles`, `#routing`) and Diagnostics (`#diagnostics`) in sidebar navigation, leaving the "Soon" badge exclusively on Settings.
  - Dedicated Routing Profiles panel (`#profiles-view`) rendering profile cards with name, read-only status badge, description, candidate priority sequence (#1 Primary, #2 Failover, etc.), retry budget (`max_retries`), timeout ceiling, and required capability tags.
  - Explicit operator disclaimer explaining read-only profile behavior without claiming runtime profile editing capabilities.
  - Dedicated Diagnostics Inspector panel (`#diagnostics-view`) rendering Gateway Runtime status, Persistence Subsystem operational state (WAL mode, availability, journal mode, degradation status with honest reason if degraded, schema version note), Subsystem Inventory counts (registered providers, catalog entries, stale models, active profiles), and Operational Warnings / Degradation Feed.
  - Manual on-demand refresh buttons (`#refresh-profiles-btn`, `#refresh-diagnostics-btn`) with in-flight loading spinners and duplicate-click guards.
  - Strictly prevents implicit background polling, implicit connection probing, or implicit discovery refreshes.
  - Zero secret or token leakage; all rendering uses `document.createElement` and `textContent`.
- **Reliability, Security Hardening & Usability Audit (Phase 8):**
  - Routing profile timeout enforcement: profile-level `timeout_seconds` is propagated to `ProviderContext` during execution.
  - Exception containment & failover: non-`ProviderError` unexpected adapter crashes are caught and normalized to retryable `ProviderUnavailableError`, preventing unhandled crashes, recording failures in telemetry/cooldown, and enabling failover to subsequent candidates.
  - Task cancellation preservation: `asyncio.CancelledError` is strictly unswallowed throughout routing and adapter lifecycles.
  - Unhandled 500 error sanitization: generic exception handler registered on FastAPI returns standard OpenAI error envelope (`api_error` / `internal_server_error`) with zero stack trace or path leakage.
  - Management error sanitization expansion: `sanitize_error` extended to eliminate `password` and `secret` patterns in addition to tokens, keys, and paths.
  - Request validation limits: added bounds on `model` (max 256), `role` (max 64), and `name` (max 64) against memory bloat.
  - Graceful shutdown lifecycle: `ProviderRegistry.aclose()` and `OllamaAdapter.aclose()` cleanly terminate underlying HTTP sessions on app lifespan shutdown before database closure.
  - Dashboard usability hardening: added redundant view switch guards preventing double-renders on hash changes, and `:focus-visible` styling for sidebar links to ensure keyboard accessibility.
- **Tests:** 161 tests across 12 test files (API v1, management API, dashboard shell/providers/catalog/profiles/diagnostics, persistence, health, auth, logging/redaction, mock provider, ollama adapter, model catalog, routing engine, reliability and security audit). All pass deterministically without external dependencies or internet access.

---

## Partially implemented

- Phase 7: Web Dashboard (Milestones P7-M1, P7-M2, P7-M3, P7-M4, and P7-M5 complete; Settings view remains planned).

---

## Not started

- Hosted provider integrations (Phase 3).
- Settings dashboard view and runtime routing profile editing.
- Packaging and portfolio release (Phase 9).
- LICENSE.

---

## Current blockers

1. Material open questions: OQ-001 license, OQ-005 credential storage — do not silently decide.
2. OQ-004 hosted providers: owner must choose first hosted vendors before Phase 3 implementation.

---

## Latest test status

**Run on 2026-11-05T19:45:00+05:30:**

| Tool | Command | Result |
|---|---|---|
| pytest | `uv run pytest -v` | 161 passed in 4.24s (exit 0) |
| ruff lint | `uv run ruff check .` | All checks passed (exit 0) |
| ruff format | `uv run ruff format --check .` | 165 files already formatted (exit 0) |
| mypy | `uv run mypy .` | Success: no issues found in 45 source files (exit 0) |

---

## Risks needing attention

- R-001/R-002: catalog honesty once providers exist.
- R-003: do not persist plaintext keys if Phase 3 starts before OQ-005 is decided.

Full list: [`RISKS_AND_OPEN_QUESTIONS.md`](RISKS_AND_OPEN_QUESTIONS.md).

---

## Next 1–3 recommended tasks

1. Review Phase 3: First Hosted Provider Integration (upon decision on OQ-004 and OQ-005).
2. Implement Phase 9: Packaging, Distribution & Portfolio Release (Docker, CI workflow, distribution docs).
3. Implement Dashboard Settings & Runtime Profile Configuration (if requested by owner).

---

## Consistency notes

- Backend health endpoint, auth, mock provider, Ollama adapter, model catalog, routing engine, persistence, OpenAI-compatible API (`/v1`), management API (`/api`), and dashboard app shell (`/dashboard`) with provider management are implemented and tested.
- All `/api` routes strictly enforce Bearer token authentication.
- Dashboard holds the user token strictly in JavaScript page memory.
- Provider probing is purely on-demand and explicit.
- Zero secret leakage guaranteed across API responses, error envelopes, and static assets.
