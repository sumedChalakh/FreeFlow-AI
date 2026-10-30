# Documentation map

**Last updated:** 2026-10-29T15:14:00+05:30  
**Purpose:** Second entry point after `AGENTS.md`. Tells every agent what to read, in what order, and which document is canonical for each topic.

---

## Reading order for every new agent

1. [`/AGENTS.md`](../AGENTS.md) — mandatory protocol.
2. [`/README.md`](../README.md) — product summary and current versus planned features.
3. This file — documentation map.
4. [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — verified reality, blockers, next task.
5. [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — phases, task IDs, exit gates.
6. [`ARCHITECTURE.md`](ARCHITECTURE.md) — system design.
7. Task-specific design docs (see table below).
8. Recent [`SESSION_LOG.md`](SESSION_LOG.md) and [`CHANGELOG.md`](CHANGELOG.md).
9. Actual source tree, Git status, and tests.

Then inspect code. If docs and code disagree, investigate and fix the docs.

---

## Canonical sources

| Topic | Canonical document |
|---|---|
| Agent workflow, definition of done | [`/AGENTS.md`](../AGENTS.md) |
| Product summary for humans | [`/README.md`](../README.md) |
| Live milestone and next task | [`PROJECT_STATUS.md`](PROJECT_STATUS.md) |
| Requirements (FR/NFR IDs) | [`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md) |
| Phases and task IDs | [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) |
| Components, request lifecycle, tradeoffs | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| SQLite entities and retention | [`DATA_MODEL.md`](DATA_MODEL.md) |
| HTTP routes and schemas | [`API_SPECIFICATION.md`](API_SPECIFICATION.md) |
| Models, discovery, free-tier honesty | [`MODEL_CATALOG.md`](MODEL_CATALOG.md) |
| Selection, failover, retries | [`ROUTING_AND_FAILOVER.md`](ROUTING_AND_FAILOVER.md) |
| Adapter interface and providers | [`PROVIDER_INTEGRATIONS.md`](PROVIDER_INTEGRATIONS.md) |
| Dashboard and UI | [`FRONTEND_SPECIFICATION.md`](FRONTEND_SPECIFICATION.md) |
| Threat model, loopback, secrets | [`SECURITY_AND_PRIVACY.md`](SECURITY_AND_PRIVACY.md) |
| Test layers and evidence | [`TESTING_STRATEGY.md`](TESTING_STRATEGY.md) |
| How to run (once code exists) | [`DEVELOPMENT_SETUP.md`](DEVELOPMENT_SETUP.md) |
| Local use vs future production | [`DEPLOYMENT.md`](DEPLOYMENT.md) |
| Folder/module inventory | [`FILE_MAP.md`](FILE_MAP.md) |
| Significant changes | [`CHANGELOG.md`](CHANGELOG.md) |
| Work sessions | [`SESSION_LOG.md`](SESSION_LOG.md) |
| Risks and unresolved decisions | [`RISKS_AND_OPEN_QUESTIONS.md`](RISKS_AND_OPEN_QUESTIONS.md) |
| Durable architecture decisions | [`decisions/`](decisions/) |
| Original owner plan (historical) | [`/FreeFlow_AI_Project_Plan_for_Cursor.md`](../FreeFlow_AI_Project_Plan_for_Cursor.md) |

Do not duplicate entire documents. Link to the canonical source.

---

## Planned versus implemented

Until `PROJECT_STATUS.md` records verified implementation evidence, treat APIs, schemas, UI pages, and adapters in these docs as **proposed**.

---

## After every meaningful change

Update the affected design doc, plus as applicable:

- `CHANGELOG.md`
- `SESSION_LOG.md`
- `PROJECT_STATUS.md`
- `FILE_MAP.md`
- related ADRs

Use real Asia/Kolkata timestamps. See `AGENTS.md`.
