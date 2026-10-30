# Security and privacy

**Last updated:** 2026-10-29T15:14:00+05:30  
**Status:** Design and policy. No security tests have been run because no application exists.

---

## Threat model (local MVP)

Assumed: a single trusted user on a Windows workstation. The gateway is not a multi-tenant SaaS.

| Threat | Mitigation (planned) |
|---|---|
| Other processes on the same machine calling the API | Local bearer token; still not a strong boundary against a malicious local user |
| LAN/WAN exposure | Bind `127.0.0.1` by default; warn if bind changes |
| DNS rebinding against localhost | Loopback bind; consider `Host` header checks; avoid wildcard CORS |
| Credential theft from repo or screenshots | `.gitignore`, redaction, no secrets in docs |
| Prompt leakage | Do not persist prompts; do not log bodies by default |
| Dependency compromise | Pin dependencies when they exist; review in Phase 8/9 |
| Provider quota abuse via open bind | Default loopback + token |

Out of MVP: defending a publicly reachable gateway, anonymous Internet users, or shared-hosting neighbors.

---

## Local API authentication

Configurable `FREEFLOW_API_TOKEN`. Compare with a constant-time comparison once implemented. Rotate by rewriting env/settings and restarting until a rotation API exists.

---

## Host binding

- Default: `127.0.0.1`.
- Binding `0.0.0.0` requires explicit config **and** a documented warning. Remote access is a later, reviewed feature (FR-029).

---

## CORS / CSRF

Dashboard should be served from the same origin as the API when practical (FastAPI mounts static, or a dev proxy). If separate origins in development:

- Allow only the known dashboard origin.
- Use CSRF protection for cookie-based auth if cookies are introduced. Prefer bearer token over cookies for the MVP unless Phase 7 decides otherwise.

---

## DNS rebinding and unauthorized local requests

- Reject unexpected `Host` headers where feasible.
- Do not enable `Access-Control-Allow-Origin: *` for credentialed routes.

---

## Credential storage and redaction

- No plaintext API keys in SQLite columns.
- OS credential store or DPAPI-backed encryption (OQ-005). If unimplemented, disable save.
- Logs: redact `Bearer`, `api_key`, `Authorization`, `sk-` like patterns conservatively without turning logs useless.
- GET responses: `has_credential` boolean only.

---

## Data retention and deletion

- Events: metadata only; proposed cap (see `DATA_MODEL.md`).
- User can delete event history from diagnostics once implemented.
- Uninstall: document files to delete (`*.db`, credential entries).

---

## Prompts and telemetry

- No prompt/response persistence by default.
- No telemetry or analytics in MVP. Adding it requires owner approval and opt-in.

---

## Dependency vulnerability management

When packages exist: documented update process; no `npm audit` theater without recording actual results. Do not claim a CVE scan passed unless it was run.

---

## Provider terms

Users are responsible for their provider accounts. FreeFlow must not encourage ToS evasion, credential sharing, or quota circumvention.

---

## Security testing (planned)

- Unauthenticated request rejected.
- Secrets absent from logs in tests.
- Health endpoint does not dump config.
- Bind address test (listens on 127.0.0.1).
- Provider GET redaction.

Known limitation: a local attacker with the user’s privileges can likely extract tokens from process memory or env. Document this honestly.
