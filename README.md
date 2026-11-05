# FreeFlow AI

**Last updated:** 2026-11-05T19:45:00+05:30  
**Status:** Phase 8 (Reliability, Security Hardening & Usability Audit) verified. 161 tests passing; ruff and mypy clean.  
**Working product name:** FreeFlow AI (provisional)

FreeFlow AI is a **local-first, provider-agnostic AI gateway** with a model catalog, intelligent routing, automatic failover, and a web dashboard.

It is intended to give a user one local API endpoint that can route requests to configured hosted AI providers or local inference runtimes. A compatible IDE or application can use that endpoint without needing to know which backend model handles each request.

This repository contains a working **backend skeleton** (FastAPI, Python 3.12), **provider abstraction** (`backend/providers/`) with verified Mock and Ollama local adapters, **model catalog** (`backend/catalog/`), **SQLite persistence** (`backend/db/`), **intelligent routing engine** (`backend/routing/`), **OpenAI-compatible HTTP gateway** (`backend/api/`), **management API** (`backend/management/`), and **Web Dashboard** (`backend/dashboard/`) supporting Overview, Provider Management with on-demand connection testing, Model Catalog Explorer with on-demand discovery refresh, Routing Profile Explorer, and Diagnostics Inspector, plus comprehensive documentation.

---

## Current status

| Item | Reality |
|---|---|
| Milestone | Phase 8 (Reliability, Security Hardening & Usability Audit) verified |
| Git | Initialized, branch `main`, remote `origin` configured |
| Backend | FastAPI app, health, Bearer auth, structured logging, Providers, Catalog, SQLite persistence, Router, `/v1` endpoints, `/api` management endpoints |
| Frontend | Dashboard Overview, Provider Management, Model Catalog Explorer, Routing Profiles, & Diagnostics implemented at `/dashboard` (HTML/CSS/JS, zero external CDN) |
| Tests | 161 passed (pytest); ruff, mypy clean |
| License | **Not chosen.** Do not assume an open-source license. |

Authoritative live status: [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md).

---

## Goals

1. One local API endpoint for multiple AI providers and local inference.
2. Discover and catalog models without treating every catalog entry as usable.
3. User-defined routing profiles for coding, general chat, reasoning, and later multimodal tasks.
4. Safe, bounded failover for eligible transient failures.
5. Transparent usage, latency, health, and routing-event visibility.
6. Provider credentials remain under the user’s control.
7. Local-only operation when a compatible local model is available.
8. Maintainable, testable, documented, and suitable as an engineering portfolio project.

## Non-goals for the MVP

- Guaranteed unlimited or guaranteed daily free tokens.
- Circumventing provider quotas or account limits.
- Bundling shared developer API keys.
- A public multi-tenant hosted service.
- Billing, subscriptions, or payments.
- Android APK implementation.
- Autonomous multi-agent workflows.
- Training foundation models.
- Universal IDE or universal model-capability promises.
- Image or audio generation in the first text-chat MVP unless a small adapter is later approved.

Full requirements: [`docs/PRODUCT_REQUIREMENTS.md`](docs/PRODUCT_REQUIREMENTS.md).

---

## High-level architecture (planned)

```text
Compatible client / IDE
        │
        ▼
  Local gateway API (loopback)
        │
        ├── Routing engine
        ├── Model catalog
        ├── Provider adapters (mock, Ollama, hosted)
        └── SQLite + secure credential store
        │
        ▼
  Web dashboard (same machine)
```

Details and diagrams: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Current features versus planned features

**Current (verified):**

- Project documentation system (`AGENTS.md`, `docs/*`).
- Proposed architecture, API, data model, security, and test strategy.
- Documentation-first workflow for future agents.
- Backend skeleton: FastAPI app with `GET /health` and Bearer token auth.
- Configuration via `pydantic-settings` with `FREEFLOW_` env prefix and `.env` support.
- Structured logging with secret redaction (`structlog` + `SecretRedactor`).
- Provider adapter interface (`ProviderAdapter`) with typed models and normalized error taxonomy.
- Mock provider adapter with deterministic failure and capability simulation.
- Ollama local provider adapter with model discovery, health check, chat completion, and honest usage metadata.
- Capability normalization (`detect_ollama_capabilities`) for streaming, vision, tools, and context window.
- Model catalog engine (`ModelCatalog`) with isolated provider discovery, concurrency safety, composite ID disambiguation (`<provider_id>:<model_id>`), stale tracking, and capability/locality filtering.
- Intelligent routing engine (`RoutingEngine`) with colon-safe model resolution, routing profiles (`default`, `coding`, `fast`, `reasoning`), health tracking with cooldown windows (`CooldownTracker`), bounded failover on retryable errors, strict non-fallback for explicit deployments, and privacy-preserving decision telemetry.
- OpenAI-compatible v1 HTTP API (`GET /v1/models`, `POST /v1/chat/completions`) with standard error normalization envelopes, Bearer token security, honest streaming disclosure, and clean dependency injection.
- SQLite persistence (`backend/db/`) with WAL mode, foreign keys, busy timeouts, sequential transactional migrations (`PRAGMA user_version`), startup restoration of providers/catalog/profiles, stale reconciliation, atomic discovery refresh, forensic corruption backups, and degraded in-memory mode.
- Authenticated management API (`backend/management/`) providing `/api/providers`, `/api/providers/{provider_id}/test`, `/api/catalog`, `/api/catalog/refresh`, `/api/profiles`, and `/api/diagnostics` with file-path sanitization and zero credential exposure.
- Web Dashboard (`backend/dashboard/`) served directly by FastAPI without external CDN dependencies, featuring in-memory token security, hash routing (`#overview`, `#providers`, `#catalog`, `#profiles`, `#diagnostics`), live probe testing, on-demand catalog discovery refresh, candidate failover sequence inspection, and runtime persistence diagnostics.
- Reliability & Security Hardening (`tests/test_reliability_and_security.py`): profile timeout enforcement, non-`ProviderError` exception containment and failover, unswallowed cancellation propagation, generic unhandled 500 mapping to OpenAI envelope without traceback leaks, management error sanitizer extension (`password`, `secret`), request payload validation bounds (`model` <= 256, `role` <= 64), graceful shutdown adapter closure (`registry.aclose()`), dashboard keyboard focus styling, and redundant view render guards.
- 161 automated tests across all 12 test modules (all pass).
- Quality tooling: ruff lint, ruff format, mypy — all clean.

**Planned (not implemented):**

- Hosted provider adapters (Phase 3).
- Streaming chat completions (Phase 6 enhancement).
- Settings view and editable routing profiles.
- CI, packaging, and Docker (Phase 9).

---

## Setup

Requires Python 3.12+ and `uv`:

1. Install dependencies:
   ```powershell
   uv sync --extra dev
   ```
2. Configure environment (optional; defaults to loopback `127.0.0.1:8000`):
   ```powershell
   Copy-Item .env.example .env
   ```
3. Run the gateway API:
   ```powershell
   uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```
4. Verify health:
   ```powershell
   Invoke-RestMethod -Uri http://127.0.0.1:8000/health -Method GET
   ```
5. Open the Web Dashboard in your browser:
   Navigate to `http://127.0.0.1:8000/dashboard` (or `http://127.0.0.1:8000/`).
   Enter your configured `FREEFLOW_API_TOKEN` in the connection panel to authenticate.
   Tokens are stored strictly in browser execution memory and never written to disk or localStorage.

## Tests and quality checks

Run test suite and linters via `uv`:

```powershell
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

Planned testing strategy: [`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md).

---

## Documentation

Start here:

1. [`AGENTS.md`](AGENTS.md) — required agent protocol.
2. [`docs/README.md`](docs/README.md) — documentation map and reading order.
3. [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — what is true today.

---

## Security

- Never commit API keys, tokens, or other secrets.
- Use `.env` locally; `.env.example` contains placeholders only.
- The planned local API binds to loopback by default.
- See [`docs/SECURITY_AND_PRIVACY.md`](docs/SECURITY_AND_PRIVACY.md).

---

## License

**Unresolved.** No license file is present. Do not copy, publish, or claim an SPDX license until the project owner chooses one.

---

## Source of the original plan

The owner-supplied planning document is preserved at [`FreeFlow_AI_Project_Plan_for_Cursor.md`](FreeFlow_AI_Project_Plan_for_Cursor.md). Canonical ongoing docs live under `docs/` and `AGENTS.md`.
