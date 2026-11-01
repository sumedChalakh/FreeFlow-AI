# Provider integrations

**Last updated:** 2026-10-31T22:20:00+05:30  
**Status:** Provider adapter interface (`backend/providers/base.py`), error hierarchy (`backend/providers/errors.py`), mock adapter (`backend/providers/mock.py`), and Ollama adapter (`backend/providers/ollama.py`) implemented and verified. Hosted adapters pending (Phase 3).

---

## Common adapter interface

Coded in `backend/providers/base.py` (`ProviderAdapter` ABC):

- `adapter_id: str`
- `async list_models(context: ProviderContext) -> list[ProviderModel]`
- `async test_connection(context: ProviderContext) -> ConnectionHealth`
- `async complete_chat(context: ProviderContext, request: ChatCompletionRequest) -> ChatCompletionResponse`

`context` supplies `base_url`, `timeout_seconds`, `api_key` (unredacted in-memory context only; never logged), and `extra_headers`.

Adapters must:

- Apply timeouts.
- Map usage when present; otherwise store `usage=None` (unknown), not fabricated zero.
- Never log Authorization headers or full keys.
- Avoid importing routing policy.

---

## Steps to add a provider

1. Confirm official API documentation, auth, model list, chat endpoint, rate limits, and terms.
2. Record the official links in this file and an ADR if it is a first-of-class vendor.
3. Implement adapter inheriting `ProviderAdapter`.
4. Register in `backend/providers/registry.py`.
5. Add mock tests: success, timeout, invalid JSON, auth failure, unsupported capability.
6. Optional manual smoke test documented as opt-in.
7. Update catalog mapping, this doc, changelog, session log, file map.

Do not modify core routing `if provider == ...` trees for each vendor.

---

## Planned first adapters

| Adapter | Priority | Official docs | Status |
|---|---|---|---|
| `mock` | Tests | N/A (fixtures in `backend/providers/mock.py`) | **Implemented & verified** (Phase 2) |
| `ollama` | Local MVP | [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md) — local endpoints `/api/tags`, `/api/chat` | **Implemented & verified** (Phase 2) |
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
