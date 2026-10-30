# Risks and open questions

**Last updated:** 2026-10-29T15:14:00+05:30  
**Status:** Active tracker. Update when items are decided or new risks appear.

Probability/impact: L/M/H.

---

## Open questions (need owner input)

| ID | Question | Why it matters | Suggested default | Status |
|---|---|---|---|---|
| OQ-001 | What license, if any, should the project use? | Publishing, portfolio, contribution | Wait; no LICENSE file until chosen | **Open** |
| OQ-002 | Initialize Git now, and which remote (GitHub, other, none)? | History, CI, backup | Init locally after docs approval; remote later | **Open** |
| OQ-003 | Confirm frontend stack (proposed React + TS + Vite) and backend (Python 3.12 + FastAPI)? | Phase 1/7 | Accept proposal | **Open** |
| OQ-004 | Which two hosted providers first, given current official docs and the owner’s credentials? | Phase 3 | Decide after owner lists keys they already have | **Open** |
| OQ-005 | Windows credential storage: `keyring` / Credential Manager vs DPAPI-encrypted SQLite vs delay credential persistence? | Security | `keyring` on Windows; disable save until it works | **Open** |
| OQ-006 | Is `GET /health` unauthenticated? | Local scanners vs information leak | Unauthenticated minimal JSON only | **Open** |
| OQ-007 | Idempotency keys for `POST /v1/chat/completions`? | Duplicate provider cost | No idempotency in first slice | **Open** |
| OQ-008 | Python installer: `pip`+`venv` vs `uv`? Node: `npm` vs `pnpm`? | Setup docs | pip+venv and npm unless owner prefers otherwise | **Open** |
| OQ-009 | Keep the product identifier `FreeFlow AI` / `freeflow-ai`? | Naming | Keep until owner renames | **Open** (provisional name) |
| OQ-010 | Allow GitHub Actions on a public repo in Phase 1? | Secrets in CI, cost | Defer CI until a remote exists | **Open** |

Agents must stop and ask rather than silently deciding OQ-001, OQ-004, OQ-005, or any paid-cloud question.

---

## Risks

| ID | Description | P | I | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| R-001 | Provider free tiers and model IDs change | H | M | Verify official docs at implementation; date-stamp labels; never promise unlimited tokens | Engineering | Open |
| R-002 | Catalog metadata incomplete or wrong | H | M | Unknown/stale flags; eligibility ≠ catalog | Engineering | Open |
| R-003 | Credential storage weaker than assumed on Windows | M | H | Feature-flag save; security review before enable | Owner + engineering | Open |
| R-004 | Cross-provider chat API incompatibility | H | M | Subset contract; per-adapter limitation docs; tests | Engineering | Open |
| R-005 | Local hardware too slow/small for local models | M | M | Honest diagnostics; hybrid hosted path | User | Open |
| R-006 | Future Android access conflicts with loopback-only bind | M | M | Explicit later pairing design; do not open 0.0.0.0 casually | Owner | Later |
| R-007 | Scope creep (agents, image gen, cloud) | M | M | MVP non-goals; approval for expansions | Owner | Open |
| R-008 | No Git history yet; easy to lose work | M | M | Initialize Git after approval (OQ-002) | Owner | Open |
| R-009 | Accidental secret commit once Git exists | M | H | `.gitignore`; never put keys in docs; hook later optional | Engineering | Open |
| R-010 | Official Ollama/provider URLs in docs go stale | M | L | Re-verify at coding time | Engineering | Open |

---

## Assumptions (explicit)

- A-001: MVP stays local-first (ADR-0001).
- A-002: First UI is the web dashboard, not Android.
- A-003: User supplies all hosted credentials.
- A-004: Text chat is the first capability slice.
- A-005: Mock provider is the source of truth for routine tests.
