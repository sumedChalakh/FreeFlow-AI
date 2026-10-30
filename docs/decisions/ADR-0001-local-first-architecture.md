# ADR-0001 — Local-first architecture

**Status:** Proposed (awaiting owner confirmation; aligned with the owner’s written plan)  
**Date:** 2026-10-29  
**Last updated:** 2026-10-29T15:14:00+05:30  
**Deciders:** Project owner (plan author); documented by the Phase 0 agent

---

## Context

FreeFlow AI needs a gateway, model catalog, routing, and dashboard. Deployment could be:

1. A cloud-hosted multi-tenant service.
2. A hybrid with a required FreeFlow account.
3. A local process on the user’s machine, talking to user-owned providers.

The owner’s plan requires a local-first MVP on Windows, user-owned credentials, and no public multi-tenant service in the first release.

---

## Decision

The MVP runs the gateway and web dashboard **on the user’s computer**. Default HTTP bind is loopback. There is no required FreeFlow cloud account. Hosted model providers are optional egress targets using **the user’s** credentials. Local inference (e.g. Ollama) is a first-class path.

---

## Alternatives considered

| Alternative | Reason not chosen for MVP |
|---|---|
| Multi-tenant hosted API | Cost, security, account system, out of non-goals |
| Required cloud control plane | Violates local-only operation when a local model exists |
| Desktop-only UI with no HTTP API | Blocks compatible IDE/clients |
| Bind `0.0.0.0` for easy phone access | Expands attack surface; Android is later |

---

## Consequences

**Positive**

- Credentials and prompts stay on the machine by default.
- Development and demos do not require paid FreeFlow infrastructure.
- Portfolio story matches a real local gateway.

**Negative / follow-ups**

- Other devices cannot reach the API until a reviewed remote-access design.
- Backups are the user’s responsibility (SQLite file + credential store).
- SQLite and a single-user threat model are insufficient if the product later becomes SaaS (would require a new ADR).

---

## When to revisit

- Owner wants a hosted public service (needs security and cost review).
- Android pairing is scheduled (FR-027 / FR-029).
- Multi-user or untrusted-network deployment is requested.

---

## Confirmation

Treat as **proposed until the owner checks the Phase 0 review checklist**. If the owner rejects local-first, stop implementation and write a superseding ADR before Phase 1.
