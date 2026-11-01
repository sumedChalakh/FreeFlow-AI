# Implementation plan

**Last updated:** 2026-10-31T23:22:00+05:30  
**Current phase:** Phase 4 (Model Catalog & Persistence), Phase 5 (Routing), and Phase 6 (API) complete and verified  
**Next approved task:** Phase 7 (Web Dashboard) or Phase 3 (Hosted Provider Integrations).

Effort figures are **ranges and estimates**, not commitments. Do not silently mark a task done; require evidence in `PROJECT_STATUS.md` and tests/logs.

---

## How to read this plan

- Task IDs are stable (`P0-T1`, `P1-T2`, …).
- Dependencies are other task IDs or phase exit gates.
- Docs/tests listed for a phase are required before that phase can be marked complete.
- Technology choices in later phases remain **proposed** until recorded in an ADR.

---

## Phase 0 — Repository audit and documentation baseline

**Status:** In progress (this work cycle). No application implementation.

**Estimated effort:** 0.5–1 day.

| ID | Task | Depends | Acceptance |
|---|---|---|---|
| P0-T1 | Inspect directory, Git, existing files | — | Findings recorded honestly |
| P0-T2 | Create `AGENTS.md` and `docs/` system | P0-T1 | Required files exist |
| P0-T3 | Define requirements, architecture, API, data model | P0-T2 | Docs internally consistent |
| P0-T4 | Record risks, assumptions, open questions, ADR-0001 | P0-T3 | Unresolved decisions explicit |
| P0-T5 | Owner review of documentation baseline | P0-T4 | Owner approval recorded in session log |

**Required docs:** Entire `docs/` set listed in `docs/README.md`.  
**Required tests:** None (no runtime).  
**Exit gate:** All required docs exist; `AGENTS.md` protocol is present; state is accurate; owner has reviewed.

---

## Phase 1 — Backend skeleton and local health

**Status:** Not started. **Do not begin until Phase 0 exit gate is met.**

**Estimated effort:** 1–2 days.

| ID | Task | Depends | Acceptance |
|---|---|---|---|
| P1-T1 | Create backend package and configuration | P0-T5 | App starts from documented commands |
| P1-T2 | `GET /health` | P1-T1 | Returns documented JSON; test passes |
| P1-T3 | Local API authentication | P1-T1 | Unauthenticated requests rejected |
| P1-T4 | Structured, redacted logging | P1-T1 | Secrets not present in log fixtures |
| P1-T5 | Format, lint, typecheck, test commands | P1-T1 | Commands documented and run |
| P1-T6 | Minimal CI workflow | Owner approval | Optional; only if approved |

**Required tests:** Health unit/API tests; auth rejection tests; no-secret-in-logs test.  
**Required docs:** `DEVELOPMENT_SETUP.md`, `API_SPECIFICATION.md` health section, `FILE_MAP.md`, changelog/session/status.  
**Exit gate:** Backend starts locally; health works; config validation works; secrets not logged; unit/API tests pass.

---

## Phase 2 — Provider abstraction and local inference

**Status:** Complete and verified (`P2-T1`, `P2-T2`, `P2-T3`, `P2-T4`, `P2-T5` all verified).  
**Estimated effort:** 2–4 days.

| ID | Task | Depends | Acceptance | Status |
|---|---|---|---|---|
| P2-T1 | Provider adapter protocol/interface | P1 exit | Interface documented and imported by tests | **Done (verified)** |
| P2-T2 | Mock provider | P2-T1 | Deterministic success/timeout/invalid/unsupported | **Done (verified)** |
| P2-T3 | Ollama adapter | P2-T1 | Connection test + chat against local runtime when present; mocks otherwise | **Done (verified)** |
| P2-T4 | Error and response normalization | P2-T1 | Shared error categories used | **Done (verified)** |
| P2-T5 | Capability metadata | P2-T3 | Unknown capabilities labeled unknown | **Done (verified)** |

**Exit gate:** Requests can be routed to a local model when configured; mock tests cover success, timeout, invalid response, unsupported capability; provider logic is separate from API routes and core routing. **(Exit gate passed; 58 tests passing).**

---

## Phase 3 — Hosted provider integrations

**Status:** Not started. First providers **not chosen** (open question OQ-004).  
**Estimated effort:** 3–6 days (one adapter at a time).

| ID | Task | Depends | Acceptance |
|---|---|---|---|
| P3-T1 | Select first hosted providers from official docs + credentials | Owner | ADR recorded |
| P3-T2 | Implement adapters one at a time | P3-T1, P2-T1 | Each has mocks |
| P3-T3 | Safe credential configuration | P1-T3, security design | No plaintext in ordinary tables if store not ready — feature stays disabled |
| P3-T4 | Usage metadata and error normalization | P3-T2 | Missing usage stored as unknown, not zero |
| P3-T5 | Document limitations and terms | P3-T2 | `PROVIDER_INTEGRATIONS.md` updated |

**Exit gate:** Mocked tests; optional manual smoke-test procedure; routine tests need no real credentials; no secrets committed; dashboard (when it exists) can distinguish configured vs unconfigured.

---

## Phase 4 — Model catalog & persistence

**Status:** Completed and verified (`P4-T1` through `P4-T5` verified with deterministic tests).  
**Estimated effort:** 2–4 days.

| ID | Task | Depends | Acceptance | Status |
|---|---|---|---|---|
| P4-T1 | Catalog schema and persistence | Data model | Standard-library SQLite schema, migrations, WAL mode, degraded fallback, startup restore | **Done (verified)** |
| P4-T2 | Discovery where official APIs support it | P2/P3 | Failures keep cache, mark stale | **Done (verified)** |
| P4-T3 | Local Ollama inventory | P2-T3 | Separate from hosted entries via composite ID | **Done (verified)** |
| P4-T4 | Manual refresh and caching | P4-T1/Service | Freshness timestamp stored | **Done (verified)** |
| P4-T5 | Capability normalization | P4-T2 | Unknown fields explicit | **Done (verified)** |

**Exit gate:** Models discoverable from implemented sources; stale/unknown represented; catalog entry is not automatically an eligible inference target; SQLite persistence preserves state across restarts and handles corrupt files gracefully. Passed on 2026-10-31.

---

## Phase 5 — Routing and automatic failover

**Status:** Completed and verified (`P5-T1` through `P5-T7` verified with deterministic tests).  
**Estimated effort:** 3–5 days.

| ID | Task | Depends | Acceptance | Status |
|---|---|---|---|---|
| P5-T1 | Explicit model selection | P4, P2 | Exact deployment used; no silent fallback | **Done (verified)** |
| P5-T2 | `auto` routing profiles | P5-T1 | Profiles prioritize candidates dynamically or configured | **Done (verified)** |
| P5-T3 | Capability filters | P5-T1 | Vision/tools/streaming filters exclude incompatible backends | **Done (verified)** |
| P5-T4 | Health and cooldown | P5-T1 | Consecutive failures trigger temporary exclusion window | **Done (verified)** |
| P5-T5 | Retry budget, backoff, `Retry-After` | P5-T4 | Bounded retries; no infinite loops | **Done (verified)** |
| P5-T6 | Error classification | P5-T5 | Auth/context/invalid abort immediately; only retryable failover | **Done (verified)** |
| P5-T7 | Structured routing-decision events | P5-T1 | Telemetry audit events record metadata without prompt text | **Done (verified)** |

**Exit gate:** Deterministic tests for selection and fallback; no infinite retries; streaming limitations enforced; decisions inspectable without secrets/prompts. Passed on 2026-10-31.

---

## Phase 6 — OpenAI-compatible API

**Status:** Completed and verified (`P6-T1`, `P6-T2`, `P6-T3`, `P6-T5` verified with integration tests; `P6-T4` streaming explicitly deferred and rejected with 400).  
**Estimated effort:** 2–4 days.

| ID | Task | Depends | Acceptance | Status |
|---|---|---|---|---|
| P6-T1 | `GET /v1/models` | P4, P1-T3 | Lists aliases, profiles, and discovered catalog models | **Done (verified)** |
| P6-T2 | `POST /v1/chat/completions` non-streaming | P5, P6-T1 | OpenAI-compatible non-streaming chat completions | **Done (verified)** |
| P6-T3 | Error normalization | P6-T2 | Stable OpenAI error envelopes (`message`, `type`, `code`, `param`) | **Done (verified)** |
| P6-T4 | Streaming | P6-T2 + failure design | Explicitly unsupported in this slice; rejected honestly with 400 | **Deferred (honestly rejected)** |
| P6-T5 | IDE/client setup docs | P6-T2 | Compatible-client configuration instructions | **Done (verified)** |

**Exit gate:** Compatible client can succeed; tests cover success and failure; compatibility limits documented; bound to loopback by default. Passed on 2026-10-31.

---

## Phase 7 — Dashboard

**Status:** Not started. Frontend stack **proposed**, not approved (OQ-003).  
**Estimated effort:** 4–7 days.

| ID | Task | Depends | Acceptance |
|---|---|---|---|
| P7-T1 | App shell, navigation, API client | Phase 1 API | Auth token handled safely |
| P7-T2 | Overview | P7-T1 | Real backend state or empty |
| P7-T3 | Model explorer | P4, P7-T1 | Filters; no fake availability |
| P7-T4 | Provider management | P3, P7-T1 | Secrets not shown after save |
| P7-T5 | Routing profile editor | P5, P7-T1 | Validation |
| P7-T6 | Usage and events | P5-T7 | Metadata only |
| P7-T7 | Settings and diagnostics | P7-T1 | Health, bind address, version |
| P7-T8 | Frontend tests | P7-T2–T7 | Main flows covered |

**Exit gate:** User can configure without editing the database by hand; UI shows actual state; secrets never revealed in full after saving; main flows work at common desktop sizes and are keyboard accessible.

---

## Phase 8 — Reliability, security, and usability

**Status:** Not started.  
**Estimated effort:** 2–4 days.

Tasks: migrations and backup/reset guidance; request-size limits; CORS/CSRF and local browser security review; logging redaction review; outage and malformed-response tests; troubleshooting; dependency review.

**Exit gate:** Security findings documented and addressed or explicitly deferred; failure behavior predictable; setup docs match implementation.

---

## Phase 9 — Packaging and portfolio release

**Status:** Not started. License required (OQ-001).  
**Estimated effort:** 2–4 days.

Tasks: reproducible install; Docker only if useful; CI; diagrams; sample config with placeholders; demo plan; license **only with owner approval**.

**Exit gate:** Fresh checkout setup via README; CI runs documented checks; demo without committed secrets; portfolio claims evidenced.

---

## Phase 10 — Later roadmap (not MVP)

Android control app; secure pairing; optional remote access; more providers; image/audio adapters; latency/cost-aware routing; optional cloud deployment after security/cost review; optional opt-in prompt capture after privacy review.

---

## Milestone view (no false precision)

| Milestone | Estimate from start of that phase | Evidence required |
|---|---|---|
| Docs approved | Owner calendar | Session-log approval |
| Local health API | 1–2 days | Passing tests |
| Local inference path | 2–4 days | Mock + optional Ollama smoke |
| Hosted adapters | 3–6 days | Mocks; no secrets in repo |
| Catalog + routing | 5–9 days | Deterministic failover tests |
| Compatible chat API | 2–4 days | Contract tests |
| Dashboard MVP | 4–7 days | UI tests + empty/error states |
| Hardening + release | 4–8 days | Security notes + CI |

Phases may overlap slightly (for example dashboard skeleton after health exists) only if it does not skip tests or docs.

---

## Current phase and next task

- **Now:** Phase 0. Implementation plan and architecture written; owner review outstanding (`P0-T5`).
- **Do not start Phase 1** until the owner approves the documentation baseline and the unresolved decisions that block coding (at least: confirm proposed stack, confirm Git init, confirm first local runtime).
- **Recommended first implementation task after approval:** `P1-T1` Create backend package and configuration.
