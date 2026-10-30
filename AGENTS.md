# AGENTS.md — FreeFlow AI

**Last updated:** 2026-10-29T15:14:00+05:30  
**Status:** Mandatory entry point for every AI agent, coding assistant, and human contributor  
**Product name:** FreeFlow AI (provisional; do not rename identifiers without owner approval)

This file governs how work is done in this repository. Read it completely before editing anything.

---

## 1. Required initialization order

Every agent or contributor entering this repository must begin in this order, including when the user says “continue,” “fix this,” or “implement the next feature”:

1. Read `/AGENTS.md` from top to bottom (this file).
2. Read `/README.md`.
3. Read `/docs/README.md` for the documentation map and canonical sources.
4. Read `/docs/PROJECT_STATUS.md` for the current milestone, verified work, blockers, and next task.
5. Read `/docs/IMPLEMENTATION_PLAN.md` and `/docs/ARCHITECTURE.md`.
6. Read the detailed design docs relevant to the assigned task (API, data model, routing, providers, frontend, security, testing, or deployment).
7. Read recent entries in `/docs/SESSION_LOG.md` and `/docs/CHANGELOG.md`.
8. Inspect the actual source tree, Git status, and tests. Do not assume documentation is current.
9. If documentation and code disagree, investigate. Treat code and test evidence as factual evidence of current behavior, then update stale documentation. Do not silently assume either source is correct.
10. Before editing, state a short plan: affected files, tests, and docs.
11. After editing, update documentation and logs before declaring the task complete.

Do not ask the user to restate project context that is already recorded accurately in the repository.

---

## 2. Current repository reality

As of the documentation baseline (2026-10-29):

- The workspace is **not a Git repository** (no `.git` directory).
- Application source code **does not exist**. There is no backend, frontend, tests, or CI.
- The only pre-existing file was `FreeFlow_AI_Project_Plan_for_Cursor.md`.
- All product features described in the design docs are **planned**, not implemented, unless `docs/PROJECT_STATUS.md` later records verified evidence.

Never claim a feature exists unless it is verified in source and, where applicable, tests.

---

## 3. Documentation-first workflow

Documentation is part of the implementation, not a cleanup step.

**Before changing code or repository structure:**

1. Consult this file and the relevant design documents.
2. Identify affected requirements, modules, interfaces, tests, and documents.
3. Implement the smallest coherent change.
4. Add or update tests.
5. Run relevant tests, linting, formatting, type checks, and build checks where configured.
6. Update the relevant documentation in the same work cycle.
7. Add a timestamped entry to `docs/CHANGELOG.md` and `docs/SESSION_LOG.md`.
8. Update `docs/PROJECT_STATUS.md` if milestones, blockers, risks, or next steps changed.
9. Update `docs/FILE_MAP.md` if files or folders were added, removed, moved, or changed in responsibility.
10. Review the diff and report what changed, why, what was tested, results, and known limitations.

A **meaningful change** includes, but is not limited to:

- Adding, removing, renaming, or moving a file or folder.
- Adding, removing, or changing a function, class, module, component, route, API endpoint, database table, schema, configuration option, environment variable, dependency, or script.
- Changing frontend behavior, UI, styling, accessibility, state management, or navigation.
- Changing backend behavior, routing, provider adapters, errors, retries, security, or data flow.
- Changing architecture, a design decision, an integration, deployment, build process, or test strategy.
- Fixing a bug, changing a test, changing a dependency version, or altering setup instructions.

---

## 4. Timestamp and audit rules

Use real timestamps generated when the change is recorded. Do not fabricate, backdate, or reuse example timestamps from the project plan.

- Timezone: **Asia/Kolkata (IST, UTC+05:30)**.
- Format: ISO 8601 with offset, for example `2026-10-29T15:20:00+05:30`.
- UTC may also be included when helpful.
- Markdown metadata: `Last updated: YYYY-MM-DDTHH:MM:SS+05:30`.
- Timestamp documentation metadata and audit logs. Do not stamp every source-code line.
- Do not bump timestamps on unrelated documents. Update a document’s timestamp only when its contents change.
- `docs/CHANGELOG.md`: user-visible or technically significant changes.
- `docs/SESSION_LOG.md`: work sessions, decisions, commands/tests run, actual results, next actions.
- `docs/decisions/`: durable architectural decisions.

`docs/SESSION_LOG.md` is append-only. Do not rewrite previous entries except to correct a clear factual error, and document that correction explicitly.

---

## 5. Engineering rules

- Work in small, reviewable increments. Do not implement all phases in one change.
- Do not add unnecessary frameworks or dependencies.
- Do not invent API behavior or claim provider capabilities without checking current official documentation.
- Prefer official provider documentation for limits, authentication, endpoints, model IDs, pricing, and terms.
- Never hardcode API keys, tokens, passwords, private URLs, or secrets in source, docs, screenshots, tests, fixtures, or Git history.
- Use `.env.example` with placeholders only. Keep real secret files Git-ignored.
- Do not log authorization headers, full API keys, sensitive prompts, or private user data by default.
- Do not send user prompts to telemetry or external analytics without clear disclosure and opt-in.
- Never bypass provider quotas, rotate accounts to evade restrictions, scrape private endpoints, or redistribute credentials.
- Respect provider terms, rate limits, model licenses, and usage policies.
- Never claim “unlimited free tokens.” Free access is provider-specific, changeable, and constrained.
- Avoid destructive shell commands and database resets unless explicitly approved and necessary.
- Do not make unrelated refactors while implementing a feature.
- Preserve backwards compatibility where practical; document breaking changes.
- Never fabricate test results, benchmarks, usage figures, or model availability.
- Ask for approval before adding paid cloud infrastructure, a hosted public service, telemetry, account systems, or any feature that creates recurring cost or expands data collection.
- Do not rename the product, package namespaces, or repository identifiers without owner approval.

---

## 6. Security and secret handling

Canonical details: [`docs/SECURITY_AND_PRIVACY.md`](docs/SECURITY_AND_PRIVACY.md).

- Bind the local API to **loopback** by default, not `0.0.0.0`.
- Do not expose secrets in GET responses, logs, or the dashboard after save (show redacted status only).
- Do not persist prompts or responses by default.
- Credential storage must be designed before it is enabled. If a secure store is not implemented, keep credential features disabled rather than storing plaintext keys in ordinary tables.
- Do not call external provider APIs during documentation-only or unit-test work unless the owner requested a manual smoke test.

---

## 7. Claims, quotas, and honesty

- A catalog entry is not automatically an eligible inference target.
- Open weights are not the same as free hosted inference.
- Do not claim universal IDE compatibility. Document the compatible API and its limits.
- Do not mark tests as passed unless they were actually run and passed. If a test cannot be run, record the exact reason and mark it as not run.
- Proposed endpoints, schemas, and UI pages are planned until implementation is verified.

---

## 8. Unresolved material decisions

Stop and ask the project owner when a material product, security, cost, licensing, or architecture decision is unresolved. Do not silently invent those decisions.

Current open questions live in [`docs/RISKS_AND_OPEN_QUESTIONS.md`](docs/RISKS_AND_OPEN_QUESTIONS.md). High-impact items include license, Git initialization, confirmed technology stack, first hosted providers, and Windows credential-storage approach.

---

## 9. Change / test / documentation checklist

A task is **not done** until applicable items are true:

- [ ] Initialization reading completed.
- [ ] Short plan stated (files, tests, docs).
- [ ] Change matches explicit acceptance criteria.
- [ ] Code matches architecture and style.
- [ ] Tests added or updated.
- [ ] Relevant tests run; real results recorded.
- [ ] Formatting, linting, type checks, and build checks run when available.
- [ ] Security implications considered.
- [ ] Relevant documentation updated.
- [ ] Timestamped changelog and session-log entries added.
- [ ] `PROJECT_STATUS.md` and `FILE_MAP.md` updated when needed.
- [ ] Final report lists changed files, behavior, tests and results, limitations, and next steps.

Do not claim a task is complete merely because code was written.

---

## 10. Phase 0 constraint

Until the project owner approves the documentation baseline:

- Do **not** implement application features.
- Do **not** install runtime dependencies.
- Do **not** call external provider APIs.
- Do **not** create backend or frontend application source trees.

The next implementation phase is Phase 1 (backend skeleton and local health), only after approval. See [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md).
