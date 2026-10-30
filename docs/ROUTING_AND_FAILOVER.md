# Routing and failover

**Last updated:** 2026-10-29T15:14:00+05:30  
**Status:** Design only. No routing engine exists.

The gateway cannot promise a fixed quantity of free tokens. Routing only chooses among **eligible** deployments the user configured.

---

## Inputs

- Requested `model` or `auto`.
- Messages and estimated input size (estimation is uncertain; document that).
- Requested output token limit.
- Task profile (`coding`, `general_chat`, `reasoning`; multimodal later).
- Tool definitions / tool-call history.
- Streaming flag.
- Multimodal parts.
- User priority rules.
- Enabled providers and health/cooldown state.

---

## Decision order

1. Validate request shape and size.
2. Resolve model or profile (`auto` → default or named profile).
3. Filter by required capabilities (unknown capability ≠ supported).
4. Filter to configured, enabled, eligible deployments.
5. Apply user priority, constraints, optional cost preference (cost preference is later unless a simple static order is in the profile).
6. Select the first remaining candidate.
7. Call adapter.
8. Normalize response and usage.
9. On retryable failure, if retry budget remains and failover is allowed, select the next eligible candidate.
10. Record outcome and per-attempt rejection reasons **without prompt text**.

---

## Explicit model versus `auto`

| Mode | Behavior |
|---|---|
| Explicit provider model ID | Use that deployment. Automatic fallback **off** unless the profile/API contract says fallback is enabled. |
| `auto` or profile alias | Choose by profile rules and filters. Failover allowed per profile `allow_fallback` and `max_attempts`. |

---

## Capability filters

Do not send:

- Image input to a deployment without verified vision support.
- Tool calls to a deployment without verified tool support.
- Requests exceeding known context limits when the limit is known.
- Stream=true to a deployment known not to stream (when streaming exists).

If capability is unknown, exclude from routes that require that capability.

---

## Error classification (proposed)

| Category | Retry same | Fail over | Notes |
|---|---|---|---|
| `auth` | No | No (unless another provider is explicitly eligible and policy allows) | Bad key |
| `permission` | No | Same as auth | |
| `invalid_request` | No | No | Client bug |
| `context_length` | No | Maybe if another model has larger context | Not a generic outage |
| `rate_limit` | After `Retry-After` if reasonable | Yes if budget | |
| `timeout` | Yes, bounded | Yes | |
| `unavailable` | Yes, bounded | Yes | 5xx / connection |
| `malformed_response` | Maybe once | Yes | |
| `unsupported` | No | Maybe other model | |

Honor `Retry-After` when present and within a configured ceiling (proposed: cap wait, e.g. a few seconds in automated path; exact cap in implementation).

Use exponential backoff with jitter. **Never retry forever.** `max_attempts` on the profile is the budget.

---

## Streaming

- Non-streaming ships first.
- If a streamed response has begun, do **not** switch providers in a way that duplicates output.
- Disconnect before first token: may retry if policy allows.
- Design of streaming failover is a Phase 6/5 follow-up, not an implicit behavior.

---

## Token and context estimation

Any local token estimate is approximate across tokenizers. If estimation is uncertain, prefer conservative rejection or passing through to the provider and classifying `context_length` errors honestly.

---

## Duplicate requests

See OQ-007. Until decided, each POST is a new attempt; clients should send a new id or accept duplicate provider calls if they retry at the HTTP layer.

---

## Testing

Deterministic tests with **mock adapters** must cover the matrix in [`TESTING_STRATEGY.md`](TESTING_STRATEGY.md) and the project plan Part G. Routine tests do not use real quota.
