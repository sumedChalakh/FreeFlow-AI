# Development setup

**Last updated:** 2026-10-29T15:14:00+05:30  
**Status:** Proposed. **Application install steps cannot be followed yet** — there is no backend or frontend package.

---

## Supported environment (MVP target)

| Item | Assumption |
|---|---|
| OS | Windows 10/11 (owner environment). Other OS later. |
| Runtime | Python 3.12+ **proposed**; Node.js LTS **proposed** for dashboard |
| Local models | Optional Ollama installation |
| Git | Recommended; repository **not initialized** as of Phase 0 |

---

## Prerequisites (when implementation exists)

1. Python 3.12+ on PATH.
2. Node.js LTS on PATH (Phase 7).
3. Copy `.env.example` to `.env` and set a local token. Never commit `.env`.
4. Optional: Ollama for local inference tests.

Do not put real API keys in `.env.example`.

---

## Installation (placeholder)

These commands are **illustrative** for after Phase 1/7 land. They will fail today.

```text
# Backend (planned)
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

```text
# Frontend (planned)
cd frontend
npm install
```

Exact package manager (`pip` vs `uv`, `npm` vs `pnpm`) is OQ-003/OQ-008.

---

## Database

SQLite file created on first backend start (planned). Path from `FREEFLOW_DATABASE_PATH`. Do not commit `*.db`.

---

## Running (planned)

- Backend: `uvicorn` on `127.0.0.1:8787`.
- Frontend: Vite dev server with proxy to the API, or static files served by the backend.

---

## Tests and quality (planned)

See `TESTING_STRATEGY.md`. No commands are runnable in this baseline.

---

## Common errors (future)

| Symptom | Likely cause |
|---|---|
| Connection refused | Backend not running |
| 401 | Token mismatch |
| Empty model list | No providers / Ollama down |
| Catalog stale | Refresh failed; cache retained |

---

## Secrets

- `.env` is gitignored.
- If you paste a key into chat or a ticket, rotate it.
- This documentation-only pass did not install dependencies and did not call provider APIs.
