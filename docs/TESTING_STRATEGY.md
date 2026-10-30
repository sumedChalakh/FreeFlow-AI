# Testing strategy

**Last updated:** 2026-10-29T15:14:00+05:30  
**Status:** Planned. **No tests have been run.** There is no test runner in the repository.

Do not mark tests passed unless they were executed. If they cannot run, record the reason.

---

## Layers

| Layer | Purpose | When |
|---|---|---|
| Unit | Routing, error classification, redaction, schema | Phase 1+ |
| Integration | SQLite, adapter registry, refresh stale behavior | Phase 2–5 |
| API contract | Health, chat completions subset, management JSON | Phase 1, 6 |
| Frontend | Validation, empty/error, main flows | Phase 7 |
| E2E | Optional Playwright against mock backend | Phase 7–9 |
| Security | Authn, redaction, bind address | Phase 1 and 8 |

Routine tests use **mock adapters** only. They must not consume real provider quota or require live keys.

---

## Routing / failover matrix

Cover at least:

| Scenario | Expected |
|---|---|
| Preferred provider succeeds | Its normalized response |
| Rate limit | Retry-After or eligible alternative |
| Timeout | Retry/fail over within budget |
| Invalid API key | Auth error; no endless retry |
| All providers fail | Normalized failure + attempts |
| Explicit model unavailable | Clear error unless fallback policy |
| Auto text | Text-capable eligible deployment |
| Auto image | Exclude non-vision |
| Context too large | Reject or larger-context model; no loop |
| Tools requested | Only verified tool support |
| Malformed JSON | Normalized error |
| Usage present | Store counts |
| Usage omitted | Unknown, not zero |
| Stream disconnect before first token | Safe retry if policy allows |
| Stream disconnect after output | No blind switch |
| Key configured | Redacted in logs/responses |
| Dashboard no providers | Empty state |
| Catalog refresh fails | Cache kept, stale |
| Local model unavailable | Report; other backend only if policy permits |

---

## Other required cases

- Invalid auth on protected routes.
- Oversized payload (when limits exist).
- Migration apply on empty and existing DB.
- Capability mismatch 4xx.

---

## Quality commands (proposed, not available yet)

Once Phase 1 exists, document exact commands in `DEVELOPMENT_SETUP.md`. Likely:

- Backend: `pytest`, `ruff`, `mypy` (if adopted).
- Frontend: `npm test`, `npm run lint`, `npm run build`.

This baseline did **not** install those tools.

---

## Evidence and reporting

For each completed implementation task, session log must include:

- Command run.
- Exit code / summary.
- Pass/fail counts if available.
- “Not run: `<reason>`” when skipped.

CI later records the same. Portfolio claims need this evidence.
