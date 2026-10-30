# API specification

**Last updated:** 2026-10-29T15:14:00+05:30  
**Status:** Proposed endpoints. **Not implemented.** Schemas will be finalized before coding each route.

Base URL (proposed): `http://127.0.0.1:8787`  
Default bind: loopback only.

---

## Authentication

| Mechanism | Proposal |
|---|---|
| Scheme | `Authorization: Bearer <FREEFLOW_API_TOKEN>` |
| Scope | All routes except possibly `GET /health` (see open question OQ-006) |
| Dashboard | Same token; never embed the token in committed frontend source |

Missing/invalid token: `401` with a normalized error body. Do not leak whether a particular header format was “almost right.”

---

## Conventions

- JSON request/response; UTF-8.
- Error shape (proposed):

```json
{
  "error": {
    "code": "unauthorized",
    "message": "Authentication required.",
    "request_id": "uuid"
  }
}
```

- Never return secret values. For providers, return `has_credential: true/false` and redacted hints only.
- Streaming: not in the first chat-completions slice. When added, use SSE or chunked `text/event-stream` compatible with the documented OpenAI subset.

---

## Gateway health

### `GET /health`

**Auth:** Proposed unauthenticated for local process supervision; confirm OQ-006.

**200 example:**

```json
{
  "status": "ok",
  "service": "freeflow-ai",
  "time": "2026-10-29T09:50:00Z"
}
```

Does not call providers. Does not include secrets.

---

## OpenAI-compatible subset

### `GET /v1/models`

Lists models the gateway is willing to expose to compatible clients. This is **not** the full catalog.

**200:** `{ "object": "list", "data": [ { "id": "...", "object": "model", "owned_by": "..." } ] }`

Document in implementation which IDs are routing aliases (`auto`, profile names) versus provider model IDs.

### `POST /v1/chat/completions`

Non-streaming first.

**Request (subset):** `model`, `messages` (`role`, `content`), optional `max_tokens`, `stream` (must be false until streaming ships), optional `tools` (rejected until supported).

**Success:** OpenAI-like `choices[0].message`, `usage` object. If the provider omitted usage, omit it or set a documented `usage_unknown` extension — **do not invent zeros**.

**Errors:** 400 validation; 401; 404 unknown model; 409/422 capability mismatch; 429 after budget exhausted; 502/503 provider failure.

**Compatibility limitations (planned disclosure):**

- Not every OpenAI field will be accepted.
- Tool calling, vision, JSON mode, and embeddings are out of the first slice unless an adapter lands with tests.
- Do not claim “works with any IDE.”

---

## Management API (dashboard)

All proposed; all authenticated; none return secrets.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/providers` | List providers (redacted) |
| POST | `/api/providers` | Create configuration |
| PATCH | `/api/providers/{provider_id}` | Update; credential replace is write-only |
| DELETE | `/api/providers/{provider_id}` | Remove config and credential_ref |
| POST | `/api/providers/{provider_id}/test` | Test connection (safe errors) |
| GET | `/api/model-catalog` | Catalog with freshness/stale flags |
| POST | `/api/model-catalog/refresh` | Manual refresh |
| GET | `/api/routing-profiles` | List profiles |
| POST | `/api/routing-profiles` | Create |
| PATCH | `/api/routing-profiles/{profile_id}` | Update |
| GET | `/api/usage` | Aggregates from `request_events` |
| GET | `/api/events` | Recent routing/request events |
| GET | `/api/settings` | Non-secret settings |
| PATCH | `/api/settings` | Update allowed keys |

Exact JSON schemas will be frozen in this document immediately before each route is implemented. Until then, treat field names as indicative.

### Provider list item (indicative)

```json
{
  "id": "uuid",
  "adapter_id": "ollama",
  "display_name": "Local Ollama",
  "base_url": "http://127.0.0.1:11434",
  "enabled": true,
  "has_credential": false,
  "last_health_ok": null,
  "last_checked_at": null
}
```

### Catalog item (indicative)

Must distinguish: cataloged, configured, capable, eligible. Include `stale`, `last_checked_at`, `is_local`, capability booleans-or-null.

### Events item (indicative)

Request id, timestamps, selected provider/model, attempts, status, error category, latency, token counts or unknown, failover flag/reason. **No messages array.**

---

## Status codes (summary)

| Code | When |
|---|---|
| 200 | Success |
| 201 | Created |
| 400 | Malformed request |
| 401 | Missing/invalid local token |
| 404 | Unknown id |
| 409 | Conflict (duplicate name) |
| 413 | Payload too large (Phase 8) |
| 422 | Semantically invalid (capability) |
| 429 | Retry budget / local rate limit |
| 500 | Unexpected local error (logged, redacted) |
| 502/503 | Upstream failure after policy |

---

## Idempotency and request IDs

- Gateway generates `request_id` if the client does not send one.
- Duplicate client request IDs: behavior TBD (OQ-007). Until specified, do not claim idempotent POSTs.

---

## What this document does not claim

These routes are not live. Contract tests do not exist. Clients cannot call this API until Phase 1+.
