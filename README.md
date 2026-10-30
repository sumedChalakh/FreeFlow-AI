# FreeFlow AI

**Last updated:** 2026-10-29T15:14:00+05:30  
**Status:** Planning / documentation baseline (Phase 0). No application runtime exists yet.  
**Working product name:** FreeFlow AI (provisional)

FreeFlow AI is a **local-first, provider-agnostic AI gateway** with a model catalog, intelligent routing, automatic failover, and a web dashboard.

It is intended to give a user one local API endpoint that can route requests to configured hosted AI providers or local inference runtimes. A compatible IDE or application can use that endpoint without needing to know which backend model handles each request.

This repository currently contains **documentation only**. Do not treat planned APIs, UI pages, or provider adapters as implemented.

---

## Current status

| Item | Reality |
|---|---|
| Milestone | Phase 0 — documentation baseline, awaiting owner approval |
| Git | Not initialized (no `.git` directory found on 2026-10-29) |
| Backend | Not started |
| Frontend | Not started |
| Tests | Not started |
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

**Planned (not implemented):**

- Backend health endpoint, configuration, and local API authentication.
- Provider adapters, catalog, routing, and OpenAI-compatible chat completions.
- Web dashboard pages.
- CI, packaging, and Docker.

---

## Setup

Runtime setup instructions will be added when Phase 1 introduces application code. Until then:

1. Read [`AGENTS.md`](AGENTS.md) if you will change the repository.
2. Read [`docs/DEVELOPMENT_SETUP.md`](docs/DEVELOPMENT_SETUP.md) for the **proposed** toolchain (pending owner approval).
3. Do not install dependencies or call provider APIs for this documentation-only baseline.

## Tests

No test runner exists yet. Planned strategy: [`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md).

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
