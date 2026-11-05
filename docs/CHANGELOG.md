# Changelog

**Last updated:** 2026-11-05T19:45:00+05:30  

Timestamped significant changes. Do not paste full diffs. Use real Asia/Kolkata times.

---

## 2026-11-05T19:45:00+05:30 — Phase 8: Reliability, Security Hardening & Usability Audit

**Summary:** Completed systematic reliability, security, and usability audit of FreeFlow AI. Enforced routing profile timeout overrides on execution context; added exception containment for unexpected adapter crashes with automatic failover and telemetry recording; preserved unswallowed `asyncio.CancelledError` throughout all async boundaries; registered generic 500 handler formatting unhandled server exceptions into OpenAI error envelopes without stack trace or filesystem leakage; expanded management API error sanitization to strip `password` and `secret` patterns; added schema bounds on request models (`model` <= 256, `role` <= 64); implemented graceful shutdown lifecycle for provider adapters (`registry.aclose()`); hardened dashboard against redundant hash view double-rendering and added `:focus-visible` styling for sidebar links to ensure keyboard accessibility. Verified with 12 new deterministic tests in `tests/test_reliability_and_security.py` (161 tests total across 12 files).

**Changed areas / files:**

- Modified `backend/routing/engine.py`: Propagated `profile.timeout_seconds` to `ProviderContext` during candidate execution; added containment for unexpected non-`ProviderError` adapter exceptions into retryable `ProviderUnavailableError` enabling failover to subsequent candidates and telemetry recording; strictly preserved `asyncio.CancelledError` without swallowing.
- Modified `backend/api/errors.py`: Registered `unhandled_exception_handler` for `Exception` to map uncaught 500 errors to standard OpenAI error envelope (`api_error` / `internal_server_error`) with zero stack trace or internal implementation leakage.
- Modified `backend/api/models.py`: Added upper bounds `max_length=256` to `model` in `ChatCompletionRequestPayload`, and `max_length=64` to `role` and `name` in `ChatMessageInput`.
- Modified `backend/management/routes.py`: Extended `sanitize_error` with regex patterns redacting `password[=:]` and `secret[=:]` credential tokens in addition to bearer tokens, api keys, and paths.
- Modified `backend/providers/registry.py`: Added async `aclose()` method to close all registered adapters with cleanup methods.
- Modified `backend/providers/ollama.py`: Added async `aclose()` method with `contextlib.suppress(Exception)` to safely close owned HTTP client connections.
- Modified `backend/main.py`: Updated lifespan shutdown to invoke `await default_registry.aclose()` before closing the SQLite database connection.
- Modified `backend/dashboard/static/dashboard.js`: Added duplicate render guard in `switchView` when already on the target view and hash is synchronized.
- Modified `backend/dashboard/static/dashboard.css`: Added `.nav-link:focus-visible` outline for keyboard navigation accessibility.
- Created `tests/test_reliability_and_security.py`: Added 12 automated unit and integration tests covering profile timeout override, unexpected exception containment and failover, explicit crash abortion, cancellation propagation, unhandled 500 OpenAI envelope mapping, payload bounds validation, comprehensive secret/path sanitization, graceful shutdown adapter and DB cleanup, and cooldown recovery after window expiry.
- Updated documentation: `README.md`, `docs/PROJECT_STATUS.md`, `docs/FILE_MAP.md`, `docs/CHANGELOG.md`, `docs/SESSION_LOG.md`.

**User-visible impact:** Operators and client applications experience improved resilience against intermittent adapter crashes, tighter timeout guarantees on latency-sensitive routing profiles, cleaner error envelopes without internal trace leaks, and improved keyboard focus visibility throughout the dashboard.

**Technical impact:** Test suite expanded from 149 to 161 tests across 12 test files. Pytest, Ruff linting, Ruff formatting, and Mypy type checks pass cleanly with zero regressions.

**Tests run and result:** `uv run pytest -v` (161 passed in 4.24s); `uv run ruff check .` (exit 0); `uv run ruff format --check .` (exit 0); `uv run mypy .` (exit 0).

---

## 2026-11-05T19:25:00+05:30 — Phase 7 Milestone P7-M5: Routing Profile Explorer & Diagnostics Inspector

**Summary:** Implemented the dedicated Routing Profile Explorer and Diagnostics Inspector views in the FreeFlow AI dashboard. Activated sidebar navigation to `#profiles` (alias `#routing`) and `#diagnostics`, leaving "Soon" badge exclusively on Settings. Added read-only routing profile cards displaying priority-ordered candidate sequences (#1 Primary, #2 Failover, etc.), retry budgets, timeouts, capability requirement tags, and read-only operator disclaimers. Added the diagnostics inspector rendering gateway runtime status, persistence subsystem health (WAL mode, availability, journal mode, degradation status with honest reason if degraded, schema version note), inventory counters, and operational warnings / degradation feed. Implemented manual refresh buttons with in-flight loading guards, backed by 6 new integration tests (29 tests in `test_dashboard.py`, 149 total across all 11 test files).

**Changed areas / files:**

- Modified `backend/dashboard/templates/dashboard.html`: Activated Routing Profiles (`#profiles`, `id="nav-link-profiles"`, `data-view="profiles"`) and Diagnostics (`#diagnostics`, `id="nav-link-diagnostics"`, `data-view="diagnostics"`) sidebar navigation items (removed disabled attributes and "Soon" badges); added `#profiles-view` panel with header, on-demand refresh button (`#refresh-profiles-btn`), profiles cards container (`#profiles-cards-container`), empty state, and error alert; added `#diagnostics-view` panel with header, on-demand refresh button (`#refresh-diagnostics-btn`), degraded alert banner, diagnostics content container (`#diagnostics-content-container`), and error alert container.
- Modified `backend/dashboard/static/dashboard.css`: Added styling for profiles cards grid, profile cards, candidate sequence boxes, candidate priority badges (`#1 Primary`, `#2 Failover`), capability requirement tags, profile parameters grid, diagnostics inspector container, section blocks, diagnostics grid, item boxes with labels/values/subtext, operational warning cards, and healthy diagnostics cards.
- Modified `backend/dashboard/static/dashboard.js`: Expanded client-side routing (`switchView`) to support `'profiles'` (with `'routing'` alias) and `'diagnostics'`; added in-memory state caches `cachedProfiles` and `cachedDiagnostics` with in-flight guards (`isFetchingProfiles`, `isFetchingDiagnostics`); implemented `fetchProfilesData()` invoking `GET /api/profiles` with Bearer auth; implemented `renderProfilesCards()` with safe DOM creation; implemented `fetchDiagnosticsData()` invoking `GET /api/diagnostics` with Bearer auth; implemented `renderDiagnostics()` structuring diagnostics into Gateway Runtime, Persistence Subsystem, Subsystem Inventory, and Operational Warnings / Degradation Feed; wired manual refresh buttons; preserved in-memory auth lifecycle across view switches.
- Modified `tests/test_dashboard.py`: Updated navigation structure assertions to verify Overview, Providers, Catalog, Profiles, and Diagnostics links are active, with only Settings remaining disabled; added 6 integration tests covering profiles view DOM elements, diagnostics view DOM elements, profiles list and card rendering contract (verifying primary and failover sequence, retry ceiling, and capability constraints), diagnostics normal and degraded contracts (verifying WAL reporting, degraded in-memory mode, and secret/path sanitization), diagnostics uninitialized database reporting, and verification that listing/refreshing profiles and diagnostics executes zero implicit background probes or discovery calls.
- Updated documentation: `README.md`, `docs/PROJECT_STATUS.md`, `docs/FILE_MAP.md`, `docs/CHANGELOG.md`, `docs/SESSION_LOG.md`.

**User-visible impact:** Operators can now navigate to the Routing Profiles view in the dashboard to inspect all built-in and restored routing profiles, review candidate failover sequences, retry ceilings, and capability requirements, and clearly understand read-only profile behavior. Operators can also navigate to the Diagnostics view to inspect live gateway operational health, persistence WAL/degradation status, subsystem resource counts, and active operational warnings.

**Technical impact:** Test suite expanded from 143 to 149 tests across 11 test files. Pytest, Ruff linting, Ruff formatting, and Mypy type checks pass cleanly with zero regressions.

**Tests run and result:** `uv run pytest -v` (149 passed in 5.47s); `uv run ruff check .` (exit 0); `uv run ruff format --check .` (exit 0); `uv run mypy .` (exit 0).

---

## 2026-11-05T18:59:00+05:30 — Phase 7 Milestone P7-M4: Model Catalog Explorer & On-Demand Discovery Refresh

**Summary:** Implemented the dedicated Model Catalog Explorer view and explicit on-demand discovery refresh in the FreeFlow AI dashboard. Enabled sidebar navigation to `#catalog`, detailed model deployment cards rendering composite IDs with safe colon handling (`ollama:llama3.2:latest`), provider ownership, locality (`Local` vs `Hosted`), capabilities tags (streaming, tools, vision), context window limits, and last discovered timestamps. Added honest representation of stale models restored from SQLite with distinct warning badges and callouts. Implemented on-demand discovery refresh (`POST /api/catalog/refresh`) with complete/partial/error summary reporting and automatic view synchronization, backed by 7 new integration tests (23 tests in `test_dashboard.py`, 143 total).

**Changed areas / files:**

- Modified `backend/dashboard/templates/dashboard.html`: Activated Model Catalog sidebar navigation item (removed disabled state and "Soon" badge); added `#catalog-view` panel with dedicated header, provider filter dropdown (`#catalog-provider-filter`), on-demand refresh button (`#refresh-catalog-btn`), refresh summary alert banner (`#catalog-refresh-alert`), cards container (`#catalog-cards-container`), empty state (`#catalog-empty-state`), and error alert container (`#catalog-error-alert`).
- Modified `backend/dashboard/static/dashboard.css`: Added styling for catalog controls, filter select dropdown, catalog cards grid, model card headers, title wraps, composite ID code blocks, metadata grid, capability tags (active and inactive states), stale warning callouts with SVG icons, and refresh summary reporting lists.
- Modified `backend/dashboard/static/dashboard.js`: Implemented client-side view routing (`switchView`) supporting `#catalog`; added in-memory catalog data caching (`cachedCatalog`), provider filter selection, DOM-safe card rendering using `document.createElement` and `textContent`, explicit on-demand discovery refresh via `POST /api/catalog/refresh` with duplicate-submission prevention (`isRefreshingCatalog`), complete/partial/error status banners with sanitized provider error messages, and post-refresh catalog view synchronization.
- Modified `tests/test_dashboard.py`: Added 7 new integration tests (23 total) covering active catalog navigation semantics, catalog view DOM elements, active vs. stale model card rendering, colon-tagged model IDs, missing optional metadata handling, verification that listing catalog never runs implicit discovery, successful catalog refresh contract, partial provider failure with sanitized error messages, provider-filtered refresh, and 404 on unregistered providers.
- Updated documentation: `README.md`, `docs/PROJECT_STATUS.md`, `docs/FILE_MAP.md`, `docs/CHANGELOG.md`, `docs/SESSION_LOG.md`.

**User-visible impact:** Operators can now navigate to the Model Catalog view in the dashboard, explore all restored and active model deployments, filter by provider, inspect supported capabilities and context window limits, clearly identify stale models awaiting discovery confirmation, and trigger explicit on-demand discovery refreshes with live status reporting.

**Technical impact:** Test suite expanded from 136 to 143 tests across 11 test files. Pytest, Ruff linting, Ruff formatting, and Mypy type checks pass cleanly with zero regressions.

**Tests run and result:** `uv run pytest -v` (143 passed in 12.47s); `uv run ruff check .` (exit 0); `uv run ruff format --check .` (exit 0); `uv run mypy .` (exit 0).

---

## 2026-11-02T01:21:00+05:30 — Phase 7 Milestone P7-M3: Provider Management & Live Probe Dashboard Interface

**Summary:** Implemented the dedicated Provider Management view and explicit live connection probing in the FreeFlow AI dashboard. Enabled sidebar navigation to `#providers`, detailed provider cards rendering non-secret configurations and locality, on-demand connection testing (`POST /api/providers/{provider_id}/test`) with per-provider latency/sanitized error reporting, duplicate test protection, and 6 new integration tests (16 tests in `test_dashboard.py`, 136 total).

**Changed areas / files:**

- Modified `backend/dashboard/templates/dashboard.html`: Activated Providers sidebar navigation item (removed disabled state and "Soon" badge), added `#providers-view` panel with dedicated header, on-demand refresh button, providers cards container (`#providers-cards-container`), empty state, and error alert containers.
- Modified `backend/dashboard/static/dashboard.css`: Added styling for providers management view, provider cards grid, metadata lists, probe status boxes with state badges, and empty states adhering to craft-floor standards.
- Modified `backend/dashboard/static/dashboard.js`: Implemented client-side view routing (`switchView`), in-memory probe result tracking (`providerProbeResults`), duplicate click prevention (`activeProbes`), explicit connection testing via `POST /api/providers/{provider_id}/test`, and safe DOM node rendering.
- Modified `tests/test_dashboard.py`: Added 6 integration tests covering active navigation semantics, provider view DOM elements, healthy/unhealthy connection probe contracts, 404 on unknown providers, safe DOM manipulation, and verification that listing/refreshing never executes implicit background probes.
- Updated documentation: `README.md`, `docs/PROJECT_STATUS.md`, `docs/FILE_MAP.md`, `docs/CHANGELOG.md`, `docs/SESSION_LOG.md`.

**User-visible impact:** Operators can now navigate to the Providers view in the dashboard, review registered provider details, and click "Test Connection" to perform explicit, on-demand reachability probes with live latency and sanitized error feedback.

**Technical impact:** Test suite increased from 130 to 136 tests across 11 files. Pytest, Ruff linting, Ruff formatting, and Mypy type checks clean.

**Tests run and result:** `uv run pytest -v` (136 passed in 6.35s); `uv run ruff check .` (exit 0); `uv run ruff format --check .` (exit 0); `uv run mypy .` (exit 0).

---

## 2026-11-02T01:05:00+05:30 — Phase 7 Milestone P7-M2: Web Dashboard App Shell & Overview

**Summary:** Implemented the FreeFlow AI Web Dashboard application shell and operational overview interface served directly by FastAPI. Added responsive, accessible dark-first UI with sidebar navigation, status pills, in-memory Bearer token authentication, metric cards (Gateway, Persistence, Providers, Catalog, Routing Profiles), provider summary table, and root redirect, backed by 10 integration tests.

**Changed areas / files:**

- Created `backend/dashboard/templates/dashboard.html`: Semantic HTML5 application shell with sidebar navigation, "Soon" pill badges on future items, top header with status pill and refresh button, in-memory token connection panel, degraded persistence warning banner, metric cards, and provider summary table.
- Created `backend/dashboard/static/dashboard.css`: Professional, zero-CDN dark-first stylesheet with high-contrast palette, accessible focus indicators, custom scrollbars, responsive layout, and state badges.
- Created `backend/dashboard/static/dashboard.js`: Zero-dependency JavaScript controller managing in-memory token lifecycle, debounced refresh, concurrent fetching of `/api/diagnostics` and `/api/providers`, XSS-safe text rendering via DOM nodes, and degraded/error state handling.
- Created `backend/dashboard/routes.py`: FastAPI routes serving `/dashboard` (HTML) and `/` (HTTP 307 redirect to `/dashboard`).
- Created `backend/dashboard/__init__.py`: Package export for `dashboard_router`.
- Modified `backend/main.py`: Mounted `/dashboard/static` static files directory and included `dashboard_router`.
- Created `tests/test_dashboard.py`: 10 integration tests verifying dashboard HTML delivery, root redirect, static asset delivery, semantic shell elements, disabled future links, zero secret leakage, strictly enforced API auth, and non-interference with existing endpoints.
- Updated documentation: `README.md`, `docs/PROJECT_STATUS.md`, `docs/FILE_MAP.md`, `docs/CHANGELOG.md`, `docs/SESSION_LOG.md`.

**User-visible impact:** Operators can open `http://127.0.0.1:8000/` or `http://127.0.0.1:8000/dashboard` in their local browser, enter their API token in-memory, and view live gateway health, persistence mode, registered providers, catalog size, and routing profiles without installing Node/npm or external dependencies.

**Technical impact:** Test suite increased from 120 to 130 tests across 11 files. Pytest, Ruff linting, Ruff formatting, and Mypy clean.

**Tests run and result:** `uv run pytest -v` (130 passed in 1.05s); `uv run ruff check .` (exit 0); `uv run ruff format --check .` (exit 0); `uv run mypy .` (exit 0).

---

## 2026-11-01T11:45:00+05:30 — Phase 7 Milestone P7-M1: Authenticated Management API Endpoints

**Summary:** Implemented secure, authenticated management API under `/api` powering the upcoming FreeFlow AI web dashboard. Added 6 management endpoints (`GET /api/providers`, `POST /api/providers/{provider_id}/test`, `GET /api/catalog`, `POST /api/catalog/refresh`, `GET /api/profiles`, `GET /api/diagnostics`) with zero secret leakage, sanitized error handling, strict Bearer authentication, and 15 new integration tests.

**Changed areas / files:**

- Created `backend/management/models.py`: Strongly-typed Pydantic schemas for provider representations, health test results, catalog entries, refresh summaries, routing profiles, and gateway diagnostics.
- Created `backend/management/routes.py`: Implemented `management_router = APIRouter(prefix="/api")` housing all 6 management endpoints, including sanitization helpers redacting tokens, keys, passwords, and file paths.
- Created `backend/management/__init__.py`: Package export for `management_router`.
- Modified `backend/api/deps.py`: Added `get_provider_registry` and `get_db_manager` FastAPI dependency injection helpers.
- Modified `backend/main.py`: Mounted `management_router` onto the main FastAPI application.
- Modified `backend/db/repositories.py`: Added automatic parent provider row insertion (`ON CONFLICT(id) DO NOTHING;`) during provider refresh transactions to prevent foreign-key violations on unseeded providers.
- Created `tests/test_management_api.py`: 15 comprehensive integration tests covering 401 unauthenticated requests across all routes, zero credential/token leakage, healthy and unhealthy provider test probes, 404 on unregistered providers, active and stale catalog querying with provider filtering and colon tag preservation, atomic refresh workflows, routing profiles inspection, and diagnostics reporting in WAL and degraded in-memory modes.
- Updated documentation: `docs/API_SPECIFICATION.md`, `docs/PROJECT_STATUS.md`, `docs/FILE_MAP.md`, `docs/CHANGELOG.md`, `docs/SESSION_LOG.md`, and `README.md`.

**User-visible impact:** External clients and management dashboards can now securely introspect registered providers, trigger connection probes, browse active/stale catalog models, run atomic discovery refreshes, view routing profiles, and inspect gateway persistence diagnostics over authenticated `/api` endpoints without leaking secrets.

**Technical impact:** Test suite increased from 105 to 120 tests (10 test files). Pytest, Ruff linting, Ruff formatting, and mypy type checks pass with 0 warnings/errors.

**Tests run and result:** `uv run pytest -v` (120 passed in 5.26s); `uv run ruff check .` (exit 0); `uv run ruff format --check .` (exit 0); `uv run mypy .` (exit 0).

---

## 2026-11-01T00:23:00+05:30 — Persistence Implementation Audit & Phase 7 Preparation

**Summary:** Completed comprehensive technical audit of SQLite persistence, lifecycle management, connection concurrency, and catalog restoration. Hardened thread synchronization using `threading.RLock`, added collision-resistant forensic corruption backups, enabled dynamic routing profile exposure in `GET /v1/models`, and added 5 regression tests covering offline startup, built-in profile preservation, multi-colon model tags, read-only write failures, and clean connection teardown.

**Changed areas / files:**

- Modified `backend/db/connection.py`: Replaced `threading.Lock` with `threading.RLock` for safe re-entrant locking, added `write_lock` property, added millisecond timestamp precision and collision retry loops in `_preserve_corrupt_file`, and guarded against duplicate corruption preservation during initialization.
- Modified `backend/db/repositories.py`: Wrapped all SQLite database transactions and cursor queries in `with self.db.write_lock:` to guarantee atomic thread isolation across both thread pool worker dispatches and direct callers.
- Modified `backend/main.py`: Enhanced `lifespan` startup to register default local `OllamaAdapter` (zero network calls), restore non-secret provider configurations into catalog contexts without credentials, restore catalog models as stale, restore custom routing profiles, and cleanly close database connections upon shutdown.
- Modified `backend/routing/engine.py`: Added `list_profiles()` and `get_all_profiles()` methods to `RoutingEngine`.
- Modified `backend/api/routes.py`: Updated `GET /v1/models` to dynamically query `engine.list_profiles()` (including restored custom profiles) and catalog entries including restored models (`include_stale=True`).
- Modified `tests/test_persistence.py`: Added 5 targeted regression tests (14 persistence tests total) proving offline startup with Ollama down, restored catalog model visibility in `GET /v1/models`, preservation of built-in routing profiles, multi-colon model tags (`ollama:deepseek-r1:7b:q4_k_m`), read-only write failure rollback, and clean connection cleanup.
- Updated documentation: `docs/PROJECT_STATUS.md`, `docs/CHANGELOG.md`, `docs/SESSION_LOG.md`, `README.md`.

**User-visible impact:** `GET /v1/models` dynamically exposes all built-in profiles, custom profiles, and restored catalog models immediately on startup without network access. Corrupt database recovery provides collision-free forensic preservation.

**Technical impact:** Test suite grew from 100 to 105 tests. All 105 pass in 0.74s. Ruff linting, ruff formatting, and mypy clean across 37 source files.

**Tests run and result:** `uv run pytest -v` (105 passed in 0.74s); `uv run ruff check .` (exit 0); `uv run ruff format --check .` (exit 0); `uv run mypy .` (exit 0).

---

## 2026-10-31T23:22:00+05:30 — Phase 4 Task P4-T1: SQLite Persistence & Startup Restoration

**Summary:** Implemented standard-library SQLite persistence for the Model Catalog, non-secret provider configurations, and custom routing profiles, complete with PRAGMA user_version schema versioning, WAL journal mode, lifespan startup restoration with stale marking, transactional rollback, honest degraded mode, and zero secret leakage.

**Changed areas / files:**

- Created `backend/db/schema.py`: PRAGMA user_version migration system with v1 DDL for `providers`, `catalog_models`, and `routing_profiles`.
- Created `backend/db/connection.py`: `DatabaseManager` providing WAL mode, busy timeouts, integrity probes (`PRAGMA quick_check`), thread-safe worker execution via `threading.Lock`, forensic corruption backup (`.corrupt.<timestamp>.db`), and observable in-memory degraded mode fallback.
- Created `backend/db/repositories.py`: `CatalogRepository` for atomic multi-model discovery upserts (`save_provider_refresh`), stale marking (`mark_provider_stale`), provider registry configuration, startup restoration, and custom routing profile persistence.
- Created `backend/db/__init__.py`: Database package exports.
- Modified `backend/config.py`: Added `db_path: str = Field("freeflow.db", ...)` supporting `FREEFLOW_DB_PATH`.
- Modified `backend/catalog/service.py`: Added repository binding, startup restoration (`restore_from_repository`), and atomic persistence transactional hooks during provider refreshes with automatic rollback on error.
- Modified `backend/main.py`: Added FastAPI `lifespan` handler to initialize `DatabaseManager`, run migrations, bind repository to `default_catalog`, restore models as stale, restore custom routing profiles into `RoutingEngine`, and report database health in `GET /health`.
- Modified `.gitignore`: Added `*.db-wal` and `*.db-shm`.
- Created `tests/test_persistence.py`: 9 integration tests covering schema creation, startup restoration, stale reconciliation, zero secret leakage, transaction rollback, concurrent WAL writes, corruption preservation and degraded mode, health reporting, and profile persistence.
- Updated documentation: `docs/IMPLEMENTATION_PLAN.md`, `docs/PROJECT_STATUS.md`, `docs/DATA_MODEL.md`, `docs/FILE_MAP.md`, `docs/CHANGELOG.md`, `docs/SESSION_LOG.md`, `README.md`.

**User-visible impact:** Discovered models and custom routing profiles persist across application restarts. `GET /health` reports detailed database availability and degraded mode status.

**Technical impact:** Test suite grew from 91 to 100 tests. All 100 pass in 0.94s. Ruff linting, formatting, and mypy clean across 37 source files.

**Tests run and result:** `uv run pytest -v` (100 passed in 0.94s); `uv run ruff check .` (exit 0); `uv run ruff format --check .` (exit 0); `uv run mypy .` (exit 0).

**Related:** Phase 4 task P4-T1.

---

## 2026-10-31T23:07:00+05:30 — Phase 6: OpenAI-Compatible API

**Summary:** Implemented the OpenAI-compatible v1 HTTP gateway exposing `GET /v1/models` and `POST /v1/chat/completions`, normalized error envelopes, Bearer authentication, honest streaming rejection, and integration tests.

**Changed areas / files:**

- Created `backend/api/models.py`: OpenAI-compliant request and response Pydantic models (`ModelListResponse`, `ModelCard`, `ChatCompletionRequestPayload`, `ChatCompletionResponsePayload`, `OpenAiErrorEnvelope`).
- Created `backend/api/deps.py`: FastAPI dependencies providing `ModelCatalog`, `RoutingEngine`, and `verify_token` Bearer authentication.
- Created `backend/api/errors.py`: Exception handlers normalizing `ProviderError`, `HTTPException`, and `RequestValidationError` into standard OpenAI error envelopes (`type`, `message`, `param`, `code`) without leaking prompts or stack traces.
- Created `backend/api/routes.py`: `v1_router` implementing `GET /v1/models` and `POST /v1/chat/completions`.
- Created `backend/api/__init__.py`: Package exports for `v1_router` and `register_error_handlers`.
- Modified `backend/main.py`: Mounted `v1_router` and registered OpenAI error handlers while preserving `/health` and `/protected`.
- Created `tests/test_api_v1.py`: 12 integration tests covering Bearer auth, model listing, non-streaming completions, profile routing, colon-tagged model routing, streaming rejection with 400, error mapping (400/404/429/504), and privacy.
- Updated documentation: `docs/IMPLEMENTATION_PLAN.md`, `docs/PROJECT_STATUS.md`, `docs/API_SPECIFICATION.md`, `docs/FILE_MAP.md`, `README.md`.

**User-visible impact:** Standard OpenAI-compatible clients and tools can configure `http://127.0.0.1:8000/v1` as their base URL and send standard chat completion and model listing requests to FreeFlow AI.

**Technical impact:** Test suite grew from 79 to 91 tests. All 91 pass in 0.43s. Ruff linting, ruff formatting, and mypy clean across 32 source files.

**Tests run and result:** `uv run pytest -v` (91 passed in 0.43s); `uv run ruff check .` (exit 0); `uv run ruff format --check .` (exit 0); `uv run mypy .` (exit 0).

**Related:** Phase 6 tasks P6-T1 through P6-T5.

---

## 2026-10-31T22:57:00+05:30 — Phase 5: Routing Engine & Automatic Failover

**Summary:** Implemented the intelligent `RoutingEngine` with colon-safe target resolution, explicit non-fallback rules, routing profiles, capability filtering, deployment health tracking and cooldown windows, bounded failover for retryable errors, and structured telemetry decision events without leaking prompt text.

**Changed areas / files:**

- Modified `backend/catalog/service.py`: Added `asyncio.Lock` per provider and snapshot reads to guarantee concurrent refresh safety and prevent dictionary mutation during iteration.
- Created `backend/routing/models.py`: `TargetResolution`, `RoutingProfile`, `FailoverAttempt`, and `RoutingDecisionEvent` data models.
- Created `backend/routing/cooldown.py`: `CooldownTracker` managing consecutive failure thresholds, temporary exclusion windows, and injectable clock.
- Created `backend/routing/resolver.py`: `ModelResolver` providing colon-safe model resolution and capability validation.
- Created `backend/routing/engine.py`: `RoutingEngine` coordinating explicit vs. profile execution, failover budget, and non-retryable error aborts.
- Created `backend/routing/__init__.py`: Package exports for routing engine, resolver, cooldown tracker, and models.
- Created `tests/test_routing.py`: 11 deterministic unit tests covering concurrency, colon parsing, explicit routing, bounded failover, non-retryable aborts, capability filtering, cooldown, and telemetry privacy.
- Updated documentation: `docs/IMPLEMENTATION_PLAN.md`, `docs/PROJECT_STATUS.md`, `docs/ROUTING_AND_FAILOVER.md`, `docs/FILE_MAP.md`, `README.md`.

**User-visible impact:** Gateway intelligently routes requests according to named profiles (`default`, `coding`, `fast`, `reasoning`) or explicit deployment IDs (`ollama:llama3.2:3b`), failing over gracefully across eligible backends upon transient failures.

**Technical impact:** Total test suite increased from 68 to 79 tests. All 79 pass in 1.05s. Ruff linting, ruff formatting, and mypy clean across 26 source files.

**Tests run and result:** `uv run pytest -v` (79 passed in 1.05s); `uv run ruff check .` (exit 0); `uv run ruff format --check .` (exit 0); `uv run mypy .` (exit 0).

**Related:** Phase 5 tasks P5-T1 through P5-T7.

---

## 2026-10-31T22:30:00+05:30 — Model Catalog & Provider Management

**Summary:** Implemented the unified `ModelCatalog` engine, `CatalogEntry` with composite IDs (`<provider_id>:<model_id>`), isolated provider discovery, stale tracking, and deterministic unit tests.

**Changed areas / files:**

- Created `backend/catalog/models.py`: `CatalogEntry` and `CatalogRefreshResult` tracking capabilities, timestamps, locality, and stale status
- Created `backend/catalog/service.py`: `ModelCatalog` service managing multi-provider discovery, per-provider fault isolation, duplicate handling, and capability filtering
- Created `backend/catalog/__init__.py`: exported `CatalogEntry`, `CatalogRefreshResult`, `ModelCatalog`, `default_catalog`
- Created `tests/test_catalog.py`: 10 unit tests covering multi-provider discovery, shared model name disambiguation, provider fault isolation, stale entry retention, model departure/reappearance, capability filtering, empty list handling, and deduplication
- Updated `docs/IMPLEMENTATION_PLAN.md`, `docs/PROJECT_STATUS.md`, `docs/MODEL_CATALOG.md`, `docs/FILE_MAP.md`, and `README.md`

**User-visible impact:** Aggregates installed local and registered mock models under unambiguous IDs. One offline or failing provider does not block catalog availability of other healthy providers.

**Technical impact:** 68 automated tests passing in 0.68s. Ruff lint, ruff format, and mypy clean across 20 source files.

**Tests run and result:** `uv run pytest -v` → 68 passed in 0.68s. `uv run ruff check .` → all passed. `uv run ruff format --check .` → 140 files formatted. `uv run mypy .` → 0 issues in 20 files.

**Related:** Phase 4 tasks P4-T2, P4-T3, P4-T4, P4-T5; session log 2026-10-31T22:27:00+05:30

---

## 2026-10-31T22:20:00+05:30 — Phase 2: Ollama Adapter and Capability Metadata (P2-T3 & P2-T5)

**Summary:** Implemented the local Ollama provider adapter (`OllamaAdapter`), capability normalization (`detect_ollama_capabilities`), and hermetic test suite using `httpx.MockTransport`. Phase 2 is complete.

**Changed areas / files:**

- Created `backend/providers/ollama.py`: `OllamaAdapter` with model discovery (`GET /api/tags`), health checking (`GET /`), chat completions (`POST /api/chat`), and error taxonomy mapping
- Added capability normalization in `backend/providers/ollama.py`: `detect_ollama_capabilities` normalizes vision, tool calling, streaming (`True`), and preserves unknown context windows as `None`
- Updated `backend/providers/__init__.py`: exported `OllamaAdapter` and `detect_ollama_capabilities`
- Created `tests/test_ollama.py`: 21 automated unit tests covering discovery, capabilities, health probes, completions, honest missing usage, and error mapping without external dependencies
- Updated `docs/IMPLEMENTATION_PLAN.md`, `docs/PROJECT_STATUS.md`, `docs/PROVIDER_INTEGRATIONS.md`, `docs/FILE_MAP.md`, and `README.md`

**User-visible impact:** The gateway can discover local Ollama models and execute chat completions against local runtimes with honest usage and error reporting.

**Technical impact:** 58 automated tests passing in 0.58s. All ruff lint, ruff format, and mypy type checks passing with 0 errors across 16 source files.

**Tests run and result:** `uv run pytest -v` → 58 passed in 0.58s. `uv run ruff check .` → all passed. `uv run ruff format --check .` → 136 files formatted. `uv run mypy .` → 0 issues in 16 files.

**Related:** Phase 2 tasks P2-T3 and P2-T5; session log 2026-10-31T22:16:00+05:30

---

## 2026-10-31T17:52:00+05:30 — Phase 2: Provider Abstraction and Mock Implementation

**Summary:** Implemented provider-agnostic adapter interface (`ProviderAdapter`), typed request/response models, normalized error taxonomy, deterministic `MockProviderAdapter`, and adapter registry.

**Changed areas / files:**

- Created `backend/providers/__init__.py` exporting public provider interfaces and types
- Created `backend/providers/base.py` defining `ProviderAdapter` ABC, `ChatMessage`, `ChatCompletionRequest`, `ChatCompletionResponse`, `UsageInfo`, `ModelCapability`, `ProviderModel`, `ConnectionHealth`, and `ProviderContext`
- Created `backend/providers/errors.py` defining `ErrorCategory` enum and `ProviderError` hierarchy with `is_retryable` property
- Created `backend/providers/mock.py` implementing `MockProviderAdapter` with deterministic responses, error simulations, model discovery, and usage tracking
- Created `backend/providers/registry.py` providing decoupled adapter management
- Created `tests/test_providers.py` adding 19 unit tests covering models, errors, mock behavior, and registry

**User-visible impact:** Foundational provider interface ready for Ollama and hosted adapters. Missing usage is honestly reported as unknown rather than fabricated zero.

**Technical impact:** 37 automated tests passing in 0.29s. Zero lint, format, or type-check issues across 14 Python source files.

**Tests run and result:** `uv run pytest -v` → 37 passed in 0.29s. `uv run ruff check .` → all passed. `uv run ruff format --check .` → 134 files formatted. `uv run mypy .` → 0 issues in 14 files.

**Related:** Phase 2 tasks P2-T1, P2-T2, P2-T4; session log 2026-10-31T17:47:00+05:30

---

## 2026-10-31T17:30:00+05:30 — Phase 1 verification documentation update

**Summary:** Updated documentation to reflect verified Phase 1 backend skeleton state: `PROJECT_STATUS.md`, `CHANGELOG.md`, `SESSION_LOG.md`, `FILE_MAP.md`, and `README.md`.

**Changed areas / files:**

- Updated `docs/PROJECT_STATUS.md` with verified implementation status, test results, and next tasks
- Updated `docs/CHANGELOG.md` (this file) with Phase 1 and documentation entries
- Updated `docs/SESSION_LOG.md` with Phase 1 verification and documentation sessions
- Updated `docs/FILE_MAP.md` with all new files (backend, tests, PRODUCT.md, uv.lock)
- Updated `README.md` with current backend status, setup instructions, and test runner

**User-visible impact:** Documentation now accurately reflects what exists and what was tested.

**Technical impact:** None — documentation only, no application code changed.

**Tests run and result:** `uv run pytest -v` → 18 passed (0.25s); `uv run ruff check .` → all passed; `uv run ruff format --check .` → 128 files formatted; `uv run mypy .` → 0 issues in 8 files. Run on 2026-10-31T17:29+05:30.

**Related:** Session log 2026-10-31T17:29:00+05:30

---

## 2026-10-30T20:20:00+05:30 — Phase 1 backend skeleton verification and fixes

**Summary:** Completed Phase 1 backend skeleton verification. Fixed bugs, created missing files, added test suite, ran all quality checks.

**Changed areas / files:**

- Created `backend/__init__.py` (package init for relative imports)
- Fixed `backend/config.py`: comment syntax error, added `env_prefix = "FREEFLOW_"`, replaced deprecated `class Config` with `model_config`
- Fixed `backend/logger.py`: import sorting, formatting (ruff)
- Fixed `backend/main.py`: import sorting, formatting, `noqa: B008` for FastAPI Depends pattern
- Fixed `pyproject.toml`: removed false MIT license classifier, added ruff/mypy/pytest config sections
- Fixed `.env.example`: aligned env var names to `FREEFLOW_API_HOST`, `FREEFLOW_API_PORT`
- Created `tests/test_health.py` (3 health endpoint tests)
- Created `tests/test_auth.py` (6 auth rejection and success tests)
- Created `tests/test_logging.py` (9 secret redaction tests)
- Updated `tests/conftest.py` formatting
- Updated `uv.lock` with dev dependencies

**User-visible impact:** Backend starts and serves health check. Auth rejects unauthenticated requests.

**Technical impact:** 18 tests pass. Ruff lint, ruff format, and mypy all clean.

**Tests run and result:** `uv run pytest -v` → 18 passed in 0.25s. `uv run ruff check .` → all passed. `uv run ruff format --check .` → all formatted. `uv run mypy .` → 0 issues in 8 files.

**Related:** Phase 1 tasks P1-T1 through P1-T5; session log 2026-10-30T20:07:00+05:30

---

## 2026-10-29T15:14:00+05:30 — Documentation baseline (Phase 0)

**Summary:** Established the documentation-first repository for FreeFlow AI. No application features were implemented.

**Changed areas / files:**

- Added `AGENTS.md`, `README.md`, `.gitignore`, `.env.example`
- Added `docs/` map and design documents (requirements, plan, status, architecture, data model, API, catalog, routing, providers, frontend, security, testing, setup, deployment, file map, risks)
- Added `docs/decisions/ADR-0001-local-first-architecture.md`
- Added this changelog and `docs/SESSION_LOG.md`
- Preserved `FreeFlow_AI_Project_Plan_for_Cursor.md`

**User-visible impact:** None in software. Contributors now have an onboarding path and live status file.

**Technical impact:** Future agents are required to read `AGENTS.md` and `docs/` before coding. Meaningful changes must update docs, changelog, and session log.

**Tests run and result:** Not run — no application or test runner. Git commands failed with `fatal: not a git repository` (expected).

**Related:** ADR-0001; session log 2026-10-29T15:06:11+05:30; `PROJECT_STATUS.md`
