# File map

**Last updated:** 2026-11-05T19:55:00+05:30  
**Status:** Inventory of repository with backend skeleton, provider adapters, Model Catalog, Routing Engine, OpenAI API, SQLite persistence, authenticated management API, Web Dashboard, Docker packaging, and GitHub Actions CI.

Update this file whenever files or folders are added, removed, moved, or change responsibility.

---

## Present now

| Path | Responsibility | Related docs |
|---|---|---|
| `AGENTS.md` | Mandatory agent protocol | This workflow |
| `README.md` | Comprehensive project overview, architecture, quickstart, API reference, verification | Product overview |
| `PRODUCT.md` | Durable product context for design tooling | Product truth |
| `Dockerfile` | Multi-stage Python 3.12-slim production container with non-root security and volume mounts | Deploy |
| `.dockerignore` | Build context ignore rules excluding caches, virtualenvs, credentials, and databases | Deploy |
| `.github/workflows/ci.yml` | GitHub Actions multi-OS CI workflow matrix (Ubuntu + Windows) | CI/CD |
| `.gitignore` | Ignore secrets, venvs, node_modules, DBs, `.impeccable/` | Security |
| `.env.example` | Placeholder environment variables with `FREEFLOW_` prefix | Setup, security |
| `FreeFlow_AI_Project_Plan_for_Cursor.md` | Owner-supplied original plan (historical) | Do not treat as live status |
| `pyproject.toml` | Package metadata, dependencies, tool config (ruff, mypy, pytest) | Setup |
| `uv.lock` | Locked dependency versions | Setup |
| `backend/__init__.py` | Backend package init | Architecture |
| `backend/main.py` | FastAPI app, `/health`, `/protected`, `/v1`, `/api` mounting, DB lifespan | API, security, persistence |
| `backend/api/__init__.py` | OpenAI API package exports | API |
| `backend/api/deps.py` | FastAPI dependencies (catalog, engine, token auth, registry, db) | API |
| `backend/api/errors.py` | OpenAI error handlers and exception mapping | API |
| `backend/api/models.py` | OpenAI-compatible request and response Pydantic models | API |
| `backend/api/routes.py` | OpenAI v1 endpoints (`/v1/models`, `/v1/chat/completions`) | API |
| `backend/management/__init__.py` | Management API package exports | API |
| `backend/management/models.py` | Management API Pydantic schemas (providers, catalog, profiles, diagnostics) | API |
| `backend/management/routes.py` | Authenticated `/api/*` management endpoints | API |
| `backend/dashboard/__init__.py` | Web Dashboard package exports | Frontend |
| `backend/dashboard/routes.py` | Web Dashboard route handlers (`/dashboard`, `/` redirect) | Frontend |
| `backend/dashboard/templates/dashboard.html` | Web Dashboard application shell HTML template | Frontend |
| `backend/dashboard/static/dashboard.css` | Web Dashboard dark-first stylesheet | Frontend |
| `backend/dashboard/static/dashboard.js` | Web Dashboard client-side controller | Frontend |
| `backend/config.py` | `pydantic-settings` config with `FREEFLOW_` prefix & DB path | Setup, security |
| `backend/logger.py` | `structlog` logger with `SecretRedactor` processor | Security, logging |
| `backend/catalog/__init__.py` | Model Catalog package exports | Catalog |
| `backend/catalog/models.py` | CatalogEntry and CatalogRefreshResult models | Catalog |
| `backend/catalog/service.py` | ModelCatalog aggregation, discovery, and persistence hooks | Catalog, persistence |
| `backend/db/__init__.py` | SQLite persistence package exports | Persistence, data model |
| `backend/db/connection.py` | DatabaseManager, WAL pragmas, degraded mode, corrupt file preservation | Persistence, data model |
| `backend/db/repositories.py` | CatalogRepository for atomic provider refreshes and profile storage | Persistence, catalog |
| `backend/db/schema.py` | PRAGMA user_version migrations and DDL for v1 schema | Persistence, data model |
| `backend/routing/__init__.py` | Routing and failover package exports | Routing |
| `backend/routing/models.py` | RoutingProfile, TargetResolution, RoutingDecisionEvent | Routing |
| `backend/routing/cooldown.py` | Deployment health tracking and cooldown windows | Routing |
| `backend/routing/resolver.py` | Colon-safe model resolution and candidate selection | Routing |
| `backend/routing/engine.py` | RoutingEngine orchestrator and bounded failover | Routing |
| `backend/providers/__init__.py` | Provider abstraction package exports | Architecture, providers |
| `backend/providers/base.py` | Provider adapter protocol, request/response models, capabilities | Providers |
| `backend/providers/errors.py` | Normalized error taxonomy and `ProviderError` hierarchy | Routing, providers |
| `backend/providers/mock.py` | Deterministic `MockProviderAdapter` for hermetic testing | Providers, testing |
| `backend/providers/ollama.py` | Local `OllamaAdapter` and capability normalization | Providers |
| `backend/providers/registry.py` | Decoupled adapter registry | Providers |
| `tests/conftest.py` | Shared pytest fixtures (`TestClient`) | Testing |
| `tests/test_api_v1.py` | OpenAI v1 API endpoints, auth, and error tests (12 tests) | Testing, API |
| `tests/test_management_api.py` | Management `/api` endpoints, auth, and sanitization tests (15 tests) | Testing, API |
| `tests/test_dashboard.py` | Web Dashboard routing, shell, navigation, provider probe, catalog explorer, routing profiles, and diagnostics inspector tests (29 tests) | Testing, Frontend |
| `tests/test_catalog.py` | Model Catalog aggregation, fault isolation, and filtering tests (10 tests) | Testing, catalog |
| `tests/test_persistence.py` | SQLite schema, startup restoration, stale reconciliation, concurrency tests (14 tests) | Testing, persistence |
| `tests/test_health.py` | Health endpoint tests (3 tests) | Testing, API |
| `tests/test_auth.py` | Auth rejection and success tests (6 tests) | Testing, security |
| `tests/test_logging.py` | Secret redaction tests (9 tests) | Testing, security |
| `tests/test_providers.py` | Provider abstraction, mock, error, and registry tests (19 tests) | Testing, providers |
| `tests/test_ollama.py` | Ollama discovery, health, chat, and capability tests (21 tests) | Testing, providers |
| `tests/test_routing.py` | Routing engine, failover, cooldown, and telemetry tests (11 tests) | Testing, routing |
| `tests/test_reliability_and_security.py` | Reliability, timeout override, exception containment, 500 mapping, input bounds, sanitization, and shutdown tests (12 tests) | Testing, Security, Reliability |
| `tests/test_packaging_and_config.py` | Configuration defaults, environment overrides, Dockerfile structure, and CI workflow tests (6 tests) | Testing, Setup, CI/CD |
| `docs/README.md` | Documentation map | All docs |
| `docs/PRODUCT_REQUIREMENTS.md` | FR/NFR | Requirements |
| `docs/IMPLEMENTATION_PLAN.md` | Phases and task IDs | Plan |
| `docs/PROJECT_STATUS.md` | Live status | Status |
| `docs/ARCHITECTURE.md` | System design | Architecture |
| `docs/DATA_MODEL.md` | SQLite design | Data |
| `docs/API_SPECIFICATION.md` | Proposed HTTP API | API |
| `docs/MODEL_CATALOG.md` | Catalog rules | Catalog |
| `docs/ROUTING_AND_FAILOVER.md` | Router policy | Routing |
| `docs/PROVIDER_INTEGRATIONS.md` | Adapters | Providers |
| `docs/FRONTEND_SPECIFICATION.md` | Dashboard | Frontend |
| `docs/SECURITY_AND_PRIVACY.md` | Threat model | Security |
| `docs/TESTING_STRATEGY.md` | Test policy | Testing |
| `docs/DEVELOPMENT_SETUP.md` | How to run | Setup |
| `docs/DEPLOYMENT.md` | Local vs future prod | Deploy |
| `docs/FILE_MAP.md` | This inventory | — |
| `docs/CHANGELOG.md` | Significant changes | Changelog |
| `docs/SESSION_LOG.md` | Session audit | Sessions |
| `docs/RISKS_AND_OPEN_QUESTIONS.md` | Risks and OQs | Risks |
| `docs/decisions/ADR-0001-local-first-architecture.md` | Local-first ADR | Architecture |

---

## Planned (not yet created)

| Path | Responsibility |
|---|---|
| `backend/app/api/` | Routes and schemas (when app is restructured) |
| `backend/app/catalog/` | Catalog services |
| `backend/app/providers/` | Adapter protocol and adapters |
| `backend/app/routing/` | Routing engine |
| `backend/app/usage/` | Events/usage |
| `backend/app/security/` | Auth, redaction, credentials |
| `backend/app/storage/` | SQLite |
| `frontend/package.json` | Dashboard package |
| `frontend/src/app/` | App shell |
| `frontend/src/features/` | Feature modules |
| `scripts/` | Dev helper scripts |
| `.github/workflows/` | CI if approved |

---

## Intentionally absent

- `frontend/` source: Phase 7 work, not started.
- `LICENSE`: not chosen (OQ-001).
