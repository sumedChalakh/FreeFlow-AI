# API specification

**Last updated:** 2026-11-01T11:40:00+05:30  
**Status:** Core OpenAI-compatible endpoints (`GET /v1/models`, `POST /v1/chat/completions`), health (`GET /health`), and authenticated management API endpoints (`/api/*`) implemented and verified. Streaming explicitly rejected with 400. Dashboard web frontend planned in P7-M2+.

Base URL (default): `http://127.0.0.1:8000` (configured via `FREEFLOW_API_HOST` and `FREEFLOW_API_PORT`)  
Default bind: loopback only (`127.0.0.1`).

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
## Authenticated management API (Phase 7, Milestone P7-M1)

All endpoints under `/api` require `Authorization: Bearer <FREEFLOW_API_TOKEN>`. Unauthenticated requests return `401 Unauthorized`.
All responses guarantee zero secret leakage. Error messages are sanitized to redact bearer tokens, API keys, passwords, and file paths.

### 1. `GET /api/providers`

Lists registered provider adapters and their runtime configuration.

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "ollama",
      "adapter_type": "ollama",
      "display_name": "Ollama (Local)",
      "base_url": "http://127.0.0.1:11434",
      "is_local": true,
      "has_credential": false,
      "timeout_seconds": 30.0,
      "max_retries": 2
    }
  ],
  "total": 1
}
```

### 2. `POST /api/providers/{provider_id}/test`

Executes an isolated health and reachability probe for the designated provider adapter using `test_connection(ctx)`. Returns `404 Not Found` if the provider ID is not registered.

**Response (200 OK - Healthy):**
```json
{
  "provider_id": "ollama",
  "status": "healthy",
  "latency_ms": 14.5,
  "error": null,
  "timestamp": 1730442000.0
}
```

**Response (200 OK - Unhealthy):**
```json
{
  "provider_id": "ollama",
  "status": "unhealthy",
  "latency_ms": 105.2,
  "error": "Connection refused to [PATH]",
  "timestamp": 1730442000.0
}
```

### 3. `GET /api/catalog`

Returns cataloged models across providers. Supports optional query parameter filtering by `provider_id`. Supports active models and models marked stale due to provider refresh issues. Unknown context windows remain `null` rather than fabricated numbers.

**Query Parameters:**
- `provider_id` (optional string): filter models belonging to a specific provider.

**Response (200 OK):**
```json
{
  "data": [
    {
      "composite_id": "ollama:deepseek-r1:7b:q4_k_m",
      "provider_id": "ollama",
      "model_id": "deepseek-r1:7b:q4_k_m",
      "display_name": "deepseek-r1:7b:q4_k_m",
      "is_local": true,
      "capabilities": {
        "supports_streaming": true,
        "supports_tools": false,
        "supports_vision": false,
        "supports_json_schema": true,
        "context_window": null
      },
      "is_stale": false,
      "discovered_at": 1730442000.0,
      "last_seen_at": 1730442000.0
    }
  ],
  "total": 1
}
```

### 4. `POST /api/catalog/refresh`

Triggers live model discovery across registered providers or a specified provider. Uses thread-safe refresh locks and commits updates to SQLite persistence.

**Request Body:**
```json
{
  "provider_id": "ollama"
}
```
*(Empty JSON object `{}` triggers refresh for all registered providers).*

**Response (200 OK):**
```json
{
  "total_refreshed": 1,
  "successful_refreshes": 1,
  "failed_refreshes": 0,
  "results": [
    {
      "provider_id": "ollama",
      "status": "success",
      "models_count": 3,
      "error": null,
      "timestamp": 1730442000.0
    }
  ]
}
```

### 5. `GET /api/profiles`

Returns all active routing profiles from `RoutingEngine`, including built-in profiles (`default`, `coding`, `fast`, `reasoning`) and any persistent custom profiles.

**Response (200 OK):**
```json
{
  "data": [
    {
      "name": "default",
      "display_name": "Default Routing Profile",
      "description": "General-purpose routing with automatic failover.",
      "candidates": ["ollama:llama3:latest"],
      "strategy": "priority",
      "cooldown_seconds": 60,
      "max_retries": 2,
      "timeout_seconds": 30.0,
      "is_builtin": true
    }
  ],
  "total": 1
}
```

### 6. `GET /api/diagnostics`

Returns sanitized gateway health, persistence status, and counts. Detects whether the gateway is running in persistent SQLite WAL mode or degraded in-memory mode. All filesystem paths and tokens are redacted.

**Response (200 OK):**
```json
{
  "gateway_status": "healthy",
  "version": "0.1.0",
  "database": {
    "persistence_mode": "sqlite_wal",
    "degraded_mode": false,
    "degraded_reason": null,
    "schema_version": 1
  },
  "providers_count": 2,
  "catalog_models_count": 5,
  "routing_profiles_count": 4,
  "timestamp": 1730442000.0
}
```

---

## Status codes (summary)

| Code | When |
|---|---|
| 200 | Success |
| 201 | Created |
| 400 | Malformed request or unsupported streaming parameter |
| 401 | Missing or invalid Bearer token (`FREEFLOW_API_TOKEN`) |
| 404 | Unknown provider id or model composite id |
| 409 | Conflict (duplicate name) |
| 422 | Semantically invalid payload |
| 429 | Upstream rate limit or routing retry budget exhausted |
| 500 | Unexpected local error (logged, redacted) |
| 502/503 | Upstream provider unavailable after failover exhausted |
| 504 | Upstream provider timeout |

---

## Idempotency and request IDs

- Gateway generates `request_id` if the client does not send one.
- Duplicate client request IDs: behavior TBD (OQ-007). Until specified, do not claim idempotent POSTs.

---

## Verification Status

All `/v1` endpoints (`/v1/models`, `/v1/chat/completions`), `/health`, and `/api` management endpoints (`/api/providers`, `/api/providers/{provider_id}/test`, `/api/catalog`, `/api/catalog/refresh`, `/api/profiles`, `/api/diagnostics`) are implemented, tested, and verified by 120 automated test cases.
