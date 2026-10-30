# Provider integrations

**Last updated:** 2026-10-29T15:14:00+05:30  
**Status:** Design only. No adapters exist. Hosted vendors are not selected yet (OQ-004).

---

## Common adapter interface (planned)

Conceptual methods (Python protocol to be coded in Phase 2):

- `adapter_id: str`
- `list_models(context) -> list[NormalizedModel]`
- `test_connection(context) -> HealthResult`
- `complete_chat(context, request) -> NormalizedChatResponse`
- `normalize_error(exc_or_response) -> GatewayError`

`context` supplies base URL, timeouts, and a **secret handle**, not a logged key.

Adapters must:

- Apply timeouts.
- Map usage when present; otherwise mark unknown.
- Never log Authorization headers or full keys.
- Avoid importing routing policy.

---

## Steps to add a provider

1. Confirm official API documentation, auth, model list, chat endpoint, rate limits, and terms.
2. Record the official links in this file and an ADR if it is a first-of-class vendor.
3. Implement adapter + fixtures.
4. Register in the adapter registry only.
5. Add mock tests: success, timeout, invalid JSON, auth failure, unsupported capability.
6. Optional manual smoke test documented as opt-in.
7. Update catalog mapping, this doc, changelog, session log, file map.

Do not modify core routing `if provider == ...` trees for each vendor.

---

## Planned first adapters

| Adapter | Priority | Official docs | Status |
|---|---|---|---|
| `mock` | Tests | N/A (fixtures) | Planned Phase 2 |
| `ollama` | Local MVP | [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md) — re-verify at implementation time | Planned Phase 2 |
| Hosted A, B | MVP target of two hosted | TBD after owner credentials and current official docs | Not chosen |

Re-verify URLs and model IDs at implementation time. Do not freeze stale model lists in this document as if they were current.

---

## Authentication and secrets

- User-supplied keys only.
- Stored via the secure strategy in `DATA_MODEL.md` / `SECURITY_AND_PRIVACY.md`.
- Test-connection errors: “authentication failed,” not the raw upstream body if it might echo the key.

---

## Streaming and tools

Document per adapter after reading official docs:

- Streaming encoding.
- Tool-call JSON shape.
- Vision part encoding.

Until verified, the gateway reports unsupported.

---

## Error normalization

Map vendor status codes and JSON error types into the categories in `ROUTING_AND_FAILOVER.md`. Keep the original vendor code in a redacted debug field only if it cannot contain secrets.

---

## Rate limits and terms

- Respect documented rate limits.
- Surface `Retry-After` when provided.
- Do not implement key rotation pools or multi-account evasion.

---

## Test fixtures

Each adapter ships recorded **synthetic** JSON fixtures (not production transcripts). No live keys in CI.

Optional smoke: documented command that the owner may run locally; results go to the session log with redaction.
