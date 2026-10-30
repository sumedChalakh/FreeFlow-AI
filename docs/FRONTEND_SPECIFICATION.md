# Frontend specification

**Last updated:** 2026-10-29T15:14:00+05:30  
**Status:** Planned UI. **No frontend package exists.** Framework is proposed (React + TypeScript + Vite) pending OQ-003.

---

## Planned versus implemented

| Surface | State |
|---|---|
| All dashboard pages | Not implemented |
| Styling system | Not chosen beyond “accessible, readable, desktop-first” |
| State management | Proposed: server state via fetch/TanStack Query **or** simple fetch hooks — decide at Phase 7 start |

Do not screenshot or demo fabricated statistics.

---

## Directory conventions (after approval)

See repository target in `FILE_MAP.md`: `frontend/src/app`, `components`, `features/{overview,models,providers,routing,usage}`, `lib`, `types`, `tests`.

---

## Page map

| Route (proposed) | Page | Purpose |
|---|---|---|
| `/` | Overview | Health, counts of configured providers, recent errors; empty state if none |
| `/models` | Model Explorer | Filters: local/hosted, capability, provider, stale |
| `/providers` | Providers | CRUD, test connection, enable/disable |
| `/routing` | Routing Profiles | Profile editor, fallback bounds |
| `/usage` | Usage and Events | Tables from `/api/usage` and `/api/events` |
| `/settings` | Settings and Diagnostics | Bind address display, token rotation UX, retention, log level |

Navigation: persistent sidebar on desktop; usable collapse on smaller widths. MVP is **desktop-first**, still readable near 1280px and 768px.

---

## Design principles

- Honest empty, loading, and error states. No skeleton charts filled with dummy numbers.
- Distinguish local vs hosted, cataloged vs eligible, free-tier vs verified-at.
- Secret inputs: `type=password`, never echo after save; show “credential on file” + replace control.
- Destructive actions (delete provider, wipe events) require confirmation.
- Labels on every control; keyboard focus visible; color not the only status signal.
- Do not store the API token in `localStorage` without a Phase 7 security note; prefer session memory or a tightly scoped approach documented then.

---

## Forms and validation

- Required fields marked.
- `base_url` must parse as URL; default local Ollama URL is a placeholder, not a claim that Ollama is running.
- `max_attempts` integer within documented bounds.
- Client validation plus backend 4xx display.

---

## API integration

- All calls to loopback management API with bearer token.
- Handle 401 by prompting for token (settings).
- Refresh catalog: disable double-submit; show stale banner if refresh fails.

---

## UI tests and demo policy

- Component/unit tests for validation and empty states.
- Later Playwright for main flows against a mock backend.
- Screenshots for portfolio must be from a running system or clearly labeled wireframes. No fake provider names that imply partnership.

---

## Accessibility baseline

- Semantic headings and landmarks.
- Contrast sufficient for text and status chips.
- Main flows keyboard accessible (Phase 7 exit gate).
