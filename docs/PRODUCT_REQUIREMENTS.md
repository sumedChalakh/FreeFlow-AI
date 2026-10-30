# Product requirements

**Last updated:** 2026-10-29T15:14:00+05:30  
**Status:** Proposed for MVP. No application implementation exists.

---

## Problem statement

Developers and local users who want to use multiple AI providers (hosted APIs and local runtimes) currently configure each client separately, juggle credentials, and have no single place to see which models they can actually use, how requests are routed, or why a call failed.

FreeFlow AI should provide a **local gateway and dashboard** so the user owns credentials, sees honest model eligibility, and can route through one compatible local endpoint with bounded failover.

---

## Target users

| User | Need |
|---|---|
| Individual developer on Windows | One local endpoint for a compatible IDE/client; local and hosted models. |
| Learner / portfolio engineer | A documented, testable system that shows real routing and adapter design. |
| Power user with Ollama | Local-only operation when a compatible local model is installed. |

Not in MVP: multi-tenant operators, billing admins, Android-only users.

---

## User journeys (MVP)

1. **First run:** User starts the local gateway, opens the dashboard, sees empty providers and a health indicator, and is not shown fabricated usage.
2. **Add local runtime:** User points at a local Ollama (or equivalent) endpoint, tests connection, sees local models listed separately from hosted catalog entries.
3. **Add hosted provider:** User pastes their own API key into a secret field; after save the key is not shown in full; a connection test reports success or a safe error.
4. **Explore models:** User filters catalog by capability, provider, and eligibility; stale metadata is labeled stale.
5. **Route a chat request:** A compatible client calls `POST /v1/chat/completions`; the gateway selects an eligible deployment and returns a normalized response.
6. **Failover:** Preferred provider rate-limits or times out; gateway retries within budget or fails over if policy allows; the event is inspectable without prompt text.
7. **Inspect usage:** User views request metadata, latency, token counts when the provider supplied them, and failover reasons.

---

## Functional requirements

| ID | Requirement | MVP |
|---|---|---|
| FR-001 | Represent a model independently from a provider-specific deployment. | Yes |
| FR-002 | Display model ID, provider, capabilities, context limits where known, streaming/tool support where known, pricing/free-tier metadata where verified, and last-checked time. | Yes |
| FR-003 | Allow manual catalog refresh and cache discovery data. | Yes |
| FR-004 | Show stale or unknown information explicitly. | Yes |
| FR-005 | Enable/disable a provider or deployment. | Yes |
| FR-006 | Do not label a catalog entry “available” unless current eligibility is known. | Yes |
| FR-007 | Keep local model inventory separate from hosted catalog entries. | Yes |
| FR-008 | Add, edit, enable, disable, and remove provider configuration. | Yes |
| FR-009 | Validate configuration without exposing secrets. | Yes |
| FR-010 | Support provider-specific credential requirements. | Yes |
| FR-011 | Offer a test-connection action with safe error messages. | Yes |
| FR-012 | Store provider health and last successful check. | Yes |
| FR-013 | Show quota information only when the provider exposes it or the user supplies a value. Never infer remaining quota from request counts alone. | Yes |
| FR-014 | Never silently use an unconfigured account or a shared key. | Yes |
| FR-015 | Route using requested model or `auto`, capabilities, health, and user priority. | Yes |
| FR-016 | Normalize provider responses and usage metadata. | Yes |
| FR-017 | Bounded retry/failover for eligible transient failures only. | Yes |
| FR-018 | Record routing outcomes without logging secrets or raw prompts. | Yes |
| FR-019 | Expose `GET /v1/models` and `POST /v1/chat/completions` for compatible clients. | Yes |
| FR-020 | Non-streaming chat completions first; streaming only after the non-streaming contract is tested. | Yes |
| FR-021 | Configurable local authentication token for the API. | Yes |
| FR-022 | Dashboard pages: Overview, Model Explorer, Providers, Routing Profiles, Usage and Events, Settings and Diagnostics. | Yes |
| FR-023 | Accessible forms; loading, error, empty states; confirmation for destructive actions. | Yes |
| FR-024 | Do not persist prompts or responses by default. | Yes |
| FR-025 | Bind the HTTP server to loopback by default. | Yes |
| FR-026 | Scheduled catalog refresh. | Later |
| FR-027 | Android control application and pairing. | Later |
| FR-028 | Image-generation or audio-generation adapters. | Later (unless a small adapter is explicitly approved) |
| FR-029 | Optional remote access with transport security. | Later |
| FR-030 | Optional opt-in prompt capture for debugging. | Later |

---

## Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-001 | Local-first: default configuration must not require a cloud-hosted FreeFlow account. |
| NFR-002 | Provider-agnostic core: routing must not be tightly coupled to one vendor SDK. |
| NFR-003 | Honest availability and metadata; no fabricated usage or model availability. |
| NFR-004 | Secrets never committed, logged in full, or returned after save. |
| NFR-005 | Deterministic automated tests using mock providers; routine tests must not consume real quota. |
| NFR-006 | Documentation updated in the same work cycle as meaningful changes (`AGENTS.md`). |
| NFR-007 | Asia/Kolkata timestamps on audit docs. |
| NFR-008 | Request size limits and predictable failure behavior (Phase 8 emphasis). |
| NFR-009 | Dashboard usable at common desktop widths and keyboard accessible for main flows. |
| NFR-010 | Structured, redacted logging. |

---

## MVP scope

In:

- Local gateway + web dashboard.
- Mock provider + local Ollama adapter + hosted adapters chosen after official-docs review and available credentials (target: at least one local and two hosted, subject to owner/credentials).
- SQLite operational metadata.
- OpenAI-compatible chat completions subset (documented limits).
- Bounded failover and inspectable events.

Out: see README non-goals and FR-026–FR-030.

---

## Acceptance criteria (product)

The first public MVP is not ready until the criteria in the project plan Part H are met. Summary:

1. User can run the gateway locally from documented instructions.
2. Dashboard shows configured providers and catalog models accurately.
3. At least one local and two hosted adapters implemented and tested, subject to credentials and terms.
4. One stable API endpoint can complete a request.
5. Failover is bounded, capability-aware, and covered by deterministic tests.
6. A client that supports the documented API can use the gateway.
7. Request metadata, latency, usage when available, and failover events are inspectable.
8. Credentials are not committed, logged, or returned by configuration endpoints.
9. Service binds to loopback by default.
10. Docs match actual behavior.
11. Automated checks pass with recorded results.
12. README states limitations; no unlimited-token or universal-IDE claims.

---

## Constraints and assumptions

**Constraints**

- Initial target OS: Windows (owner environment). Other OS support is later unless approved.
- User-owned credentials only.
- Provider terms and rate limits apply.
- Product name is provisional.

**Assumptions (pending confirmation)**

- Python/FastAPI backend and React/TypeScript/Vite frontend are acceptable (see open questions).
- Ollama is an acceptable first local runtime.
- SQLite is sufficient for MVP persistence.
- Owner will approve Git initialization and a license before public release.

If an assumption is wrong, update this document and `RISKS_AND_OPEN_QUESTIONS.md` rather than coding around it silently.
