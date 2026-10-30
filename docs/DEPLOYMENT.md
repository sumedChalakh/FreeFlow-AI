# Deployment

**Last updated:** 2026-10-29T15:14:00+05:30  
**Status:** Local-use guidance. No packaging artifacts exist.

---

## MVP deployment model

Run the gateway and dashboard **on the user’s computer**. This is not a production multi-tenant service.

1. Configure `.env` with loopback host and a strong local token.
2. Start the backend (once it exists) bound to `127.0.0.1`.
3. Open the dashboard in a local browser.
4. Add **your** provider credentials through the UI when that UI exists.

Do not expose the local API to a public network without authentication, transport security, access controls, and an explicit deployment review.

---

## What is not in MVP

- Docker images (optional later if useful for local deploy).
- Kubernetes, cloud VMs, or a hosted FreeFlow cloud.
- Reverse proxies on `0.0.0.0` without review.
- Shared instance for multiple untrusted users.

---

## Backup and data location (planned)

When SQLite exists:

- Backup: copy the database file while the app is stopped, or use SQLite backup API later.
- Credentials: backup/export of OS credential entries is a documented limitation until a guided backup exists.
- Reset: only with explicit owner approval; never the default first-run path.

---

## Future production checklist (not started)

TLS, strong auth, rate limits, audit logs, multi-user isolation, threat model update, cost review. None of these are claimed done.
