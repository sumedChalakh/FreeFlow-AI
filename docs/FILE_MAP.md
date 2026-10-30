# File map

**Last updated:** 2026-10-29T15:14:00+05:30  
**Status:** Inventory of the documentation-only repository. Application trees are **planned**, not present.

Update this file whenever files or folders are added, removed, moved, or change responsibility.

---

## Present now

| Path | Responsibility | Related docs |
|---|---|---|
| `AGENTS.md` | Mandatory agent protocol | This workflow |
| `README.md` | Human project summary | Product overview |
| `.gitignore` | Ignore secrets, venvs, node_modules, DBs | Security |
| `.env.example` | Placeholder env names only | Setup, security |
| `FreeFlow_AI_Project_Plan_for_Cursor.md` | Owner-supplied original plan (historical) | Do not treat as live status |
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
| `docs/DEVELOPMENT_SETUP.md` | How to run (future) | Setup |
| `docs/DEPLOYMENT.md` | Local vs future prod | Deploy |
| `docs/FILE_MAP.md` | This inventory | — |
| `docs/CHANGELOG.md` | Significant changes | Changelog |
| `docs/SESSION_LOG.md` | Session audit | Sessions |
| `docs/RISKS_AND_OPEN_QUESTIONS.md` | Risks and OQs | Risks |
| `docs/decisions/ADR-0001-local-first-architecture.md` | Local-first ADR | Architecture |

---

## Planned after documentation approval (do not create in Phase 0)

| Path | Responsibility |
|---|---|
| `backend/pyproject.toml` | Backend package metadata |
| `backend/app/main.py` | ASGI entry |
| `backend/app/api/` | Routes and schemas |
| `backend/app/core/` | Config, errors, logging |
| `backend/app/catalog/` | Catalog services |
| `backend/app/providers/` | Adapter protocol and adapters |
| `backend/app/routing/` | Routing engine |
| `backend/app/usage/` | Events/usage |
| `backend/app/security/` | Auth, redaction, credentials |
| `backend/app/storage/` | SQLite |
| `backend/tests/` | Unit, integration, contract |
| `frontend/package.json` | Dashboard package |
| `frontend/src/app/` | App shell |
| `frontend/src/features/` | Feature modules |
| `scripts/` | Dev helper scripts |
| `.github/workflows/` | CI if approved |

---

## Intentionally absent

- `backend/` and `frontend/` source: Phase 0 forbids them.
- `LICENSE`: not chosen (OQ-001).
- `.git/`: Git was not initialized during this documentation pass.
