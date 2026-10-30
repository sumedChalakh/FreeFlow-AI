# FreeFlow AI — Project Plan and Cursor Master Instructions

**Document type:** Product vision, engineering plan, architecture baseline, and AI-coding-agent operating instructions  
**Working product name:** FreeFlow AI  
**Status:** Planning / documentation-first  
**Initial target:** Local-first AI gateway and web dashboard on Windows  
**Timezone for project activity logs:** Asia/Kolkata (IST, UTC+05:30)  
**Date prepared:** 2026-10-29

> **Important:** The name FreeFlow AI is provisional. Do not rename repositories, package namespaces, or product identifiers without the project owner's approval.

---

# PART A — INSTRUCTIONS FOR CURSOR

## 1. Your role

Act as the project's senior software architect, technical lead, implementation engineer, test engineer, security reviewer, and documentation maintainer.

Build this project incrementally. Prefer a small, reliable, tested implementation over a large amount of unverified code.

The project owner wants to learn from the codebase and use the project as a serious AI/ML engineering portfolio project. Explain important design choices in the documentation. Do not hide complexity behind unexplained abstractions.

## 2. First task: documentation only

**Do not begin implementing the application in your first pass.**

First inspect the repository and the existing files. Preserve useful work if a repository already exists. Then create or update the documentation baseline described below.

Your first response/work cycle must:

1. Inspect the existing directory, Git status, current branch, and existing project files. Do not delete, overwrite, reset, or reorganize existing work without understanding it.
2. Identify the current state: empty repository, partially implemented project, or existing application.
3. Create/update `AGENTS.md` at the repository root. This is the mandatory entry point for future AI agents and contributors.
4. Create/update `README.md` and the documents in `docs/` listed in Part C.
5. Write a phased implementation plan, acceptance criteria, risks, testing strategy, and proposed repository structure.
6. Record any unresolved design questions and assumptions. Do not silently invent decisions that materially affect security, cost, licensing, or architecture.
7. Check all documentation for consistency.
8. Summarize the files created/updated, decisions made, unresolved questions, and the next recommended task.
9. Stop before application implementation and ask the project owner to review/approve the documentation baseline.

If there are existing source files, document them accurately. Do not claim features exist unless verified.

## 3. Mandatory documentation-first policy

Documentation is part of the implementation, not an optional task to do at the end.

Before changing code, consult the project entry-point documentation and relevant design documents. After every meaningful code or repository change, update the relevant documentation in the same work cycle.

A meaningful change includes, but is not limited to:

- Adding, removing, renaming, or moving a file or folder.
- Adding, removing, or changing a function, class, module, component, route, API endpoint, database table, schema, configuration option, environment variable, dependency, or script.
- Changing frontend behavior, UI, styling system, accessibility, state management, or navigation.
- Changing backend behavior, routing logic, provider adapters, errors, retries, security, or data flow.
- Changing architecture, a design decision, an integration, deployment, build process, or test strategy.
- Fixing a bug, changing a test, changing a dependency version, or altering setup instructions.

For each meaningful change:

1. Read `AGENTS.md` and the relevant docs before making the change.
2. Identify the affected requirements, modules, interfaces, tests, and documents.
3. Implement the smallest coherent change.
4. Add or update tests.
5. Run relevant tests, linting, formatting, type checks, and build checks where configured.
6. Update the relevant documentation, including setup instructions or API references when needed.
7. Add a timestamped entry to `docs/CHANGELOG.md` and `docs/SESSION_LOG.md`.
8. Update `docs/PROJECT_STATUS.md` if milestones, blockers, risks, or next steps changed.
9. Update `docs/FILE_MAP.md` if files or folders were added, removed, moved, or changed in responsibility.
10. Review the diff and report what changed, why, what was tested, results, and known limitations.

Do not mark tests as passed unless they were actually run and passed. If a test cannot be run, record the exact reason and mark it as not run.

## 4. Timestamp and audit conventions

Use real timestamps generated at the time the change is recorded. Do not fabricate past timestamps or backdate entries.

- Use ISO 8601 timestamps.
- Include the local timestamp with the `+05:30` offset for Asia/Kolkata.
- UTC may also be included when helpful.
- Example format: `2026-10-29T15:30:00+05:30` (example only; use the actual current time when writing an entry).
- In Markdown front matter or metadata, include `Last updated: YYYY-MM-DDTHH:MM:SS+05:30`.
- In `docs/CHANGELOG.md`, record user-visible or technically significant changes.
- In `docs/SESSION_LOG.md`, record work sessions, decisions, commands/tests run, results, and next actions.
- In `docs/DECISIONS.md` or an ADR, record durable architectural decisions and their rationale.

Do not add timestamps to every source-code line or every source file. Keep source files clean. Timestamp the documentation metadata and audit logs instead. Do not modify timestamps on unrelated documents just to make them look current; update a document's timestamp when its contents change.

## 5. Instructions for every future AI agent

Every AI agent, coding assistant, or human contributor entering this repository must begin in this order:

1. Read `/AGENTS.md` from top to bottom.
2. Read `/README.md`.
3. Read `/docs/README.md` to understand the documentation map and reading order.
4. Read `/docs/PROJECT_STATUS.md` to learn the current milestone, what is implemented, what is incomplete, known blockers, and the next task.
5. Read `/docs/IMPLEMENTATION_PLAN.md` and `/docs/ARCHITECTURE.md`.
6. Read the relevant detailed design docs for the task (API, data model, routing, provider adapters, frontend, security, testing, or deployment).
7. Read the recent entries in `/docs/SESSION_LOG.md` and `/docs/CHANGELOG.md`.
8. Inspect the actual source code, Git status, and tests before assuming the documentation is current.
9. If documentation and code disagree, investigate and resolve the discrepancy. Treat the actual code and test evidence as factual evidence of current behavior, and update stale documentation. Do not silently assume either source is correct.
10. Before editing, state a short plan listing affected files, tests, and docs.
11. After editing, update the docs and logs before declaring the task complete.

If a new agent starts with an instruction such as “continue,” “fix this,” or “implement the next feature,” it must not skip the initialization steps. It should not ask the user to repeat project context already recorded accurately in the repository.

## 6. Engineering rules

- Work in small, reviewable increments.
- Do not implement all phases in one giant change.
- Do not add unnecessary frameworks or dependencies.
- Do not invent API behavior or claim provider capabilities without checking current official documentation.
- Prefer official provider documentation for limits, authentication, endpoint behavior, model IDs, pricing, and terms.
- Never hardcode API keys, tokens, passwords, private URLs, or secrets in source code, documentation, screenshots, tests, fixtures, or Git history.
- Use `.env.example` with placeholders only. Ensure real secret files are ignored by Git.
- Do not log authorization headers, full API keys, sensitive prompts, or private user data by default.
- Do not send a user's prompts to telemetry or external analytics without clear disclosure and opt-in.
- Never bypass provider quotas, rotate accounts to evade restrictions, scrape private endpoints, or redistribute provider credentials.
- Respect provider terms, rate limits, model licenses, and usage policies.
- Never claim “unlimited free tokens.” Free access is provider-specific, changeable, and constrained by quotas, model availability, and terms.
- Avoid destructive shell commands and database resets unless explicitly approved and clearly necessary.
- Do not make unrelated refactors while implementing a feature.
- Preserve backwards compatibility where practical; document breaking changes.
- Use UTC/local timestamps honestly; never fabricate test results, benchmark results, usage figures, or model availability.
- Ask for approval before adding paid cloud infrastructure, a hosted public service, telemetry, account systems, or any feature that creates recurring cost or materially expands data collection.

## 7. Definition of a completed task

A task is complete only when all applicable items are true:

- The change satisfies explicit acceptance criteria.
- Code is consistent with the architecture and style.
- Appropriate tests were added or updated.
- Relevant tests were run, with real results recorded.
- Formatting, linting, type checks, and build checks were run when available.
- Security implications were considered.
- Relevant documentation was updated.
- Timestamped changelog and session-log entries were added.
- Project status and file map were updated when needed.
- The final report lists changed files, behavior, tests and results, limitations, and next steps.

Do not claim a task is complete merely because code was written.

---

# PART B — PRODUCT VISION AND SCOPE

## 8. Product summary

FreeFlow AI is a **local-first, provider-agnostic AI gateway with a model catalog, intelligent routing, automatic failover, and a web dashboard**.

It gives a user one local API endpoint that can route requests to configured hosted AI providers or local inference runtimes. A compatible IDE or application can use that endpoint without needing to know which backend model handles each request.

The dashboard allows the user to discover model metadata, configure their own provider credentials, select models by use case, define fallback priorities, and inspect usage and failures.

An Android control application may be added in a later phase. It is not part of the first MVP.

### Product goals

1. Provide one local API endpoint for multiple AI providers and local inference.
2. Discover and catalog models without assuming that every discovered model is usable.
3. Support user-defined routing profiles for coding, general chat, reasoning, and supported multimodal tasks.
4. Implement safe, bounded failover for eligible transient failures.
5. Provide transparent usage, latency, health, and routing-event visibility.
6. Keep provider credentials under the user's control.
7. Support local-only operation when the user has a compatible local model.
8. Be maintainable, testable, documented, and suitable for a public engineering portfolio.

### Non-goals for the MVP

- Guaranteed unlimited or guaranteed daily free token supply.
- Circumventing provider quotas, restrictions, or account limits.
- Bundling shared developer API keys for all users.
- A public multi-tenant hosted service.
- Billing, subscriptions, or payments.
- Android APK implementation.
- Autonomous agents or complex multi-agent workflows.
- Training foundation models.
- A universal promise that every IDE or every model capability will work.
- Image generation or audio generation in the first text-chat MVP unless a small, well-defined adapter is later approved.

## 9. Core product principles

### Local-first
The gateway and dashboard should run on the user's computer for the MVP. The default configuration must not require a cloud-hosted FreeFlow account.

### Provider-agnostic
Routing and application logic must not be tightly coupled to a single provider SDK or request schema.

### Honest availability
A model listed in a catalog is not necessarily available to a given user. Clearly distinguish catalog presence, provider support, user configuration, model capability, and current eligibility.

### User-owned credentials
The user supplies credentials for hosted providers. Credentials must be handled securely and must not be shared between users.

### Observable routing
For every request, the system should record a safe, inspectable routing outcome: selected provider/model, elapsed time, attempt count, status, failover reason, and token counts when supplied by the provider. Do not store raw prompt content by default.

### Safe failover
Retries must be bounded. Only retry/fail over for appropriate errors. Do not retry indefinitely, repeat non-idempotent actions blindly, or switch backend after partial streamed output in a way that duplicates responses.

### Capability-aware selection
Do not send image input to a text-only model or tool calls to a backend that cannot handle them. Model capability metadata must influence routing.

### Documentation as a requirement
The project must remain understandable to a new agent or developer entering the repository months later.

---

# PART C — REQUIRED DOCUMENTATION SYSTEM

Create this structure during the documentation-first phase. Adapt it only if the existing repository has a compelling reason to differ, and document the decision.

```text
/
├── AGENTS.md
├── README.md
├── .gitignore
├── .env.example
├── docs/
│   ├── README.md
│   ├── PRODUCT_REQUIREMENTS.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── PROJECT_STATUS.md
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── API_SPECIFICATION.md
│   ├── MODEL_CATALOG.md
│   ├── ROUTING_AND_FAILOVER.md
│   ├── PROVIDER_INTEGRATIONS.md
│   ├── FRONTEND_SPECIFICATION.md
│   ├── SECURITY_AND_PRIVACY.md
│   ├── TESTING_STRATEGY.md
│   ├── DEVELOPMENT_SETUP.md
│   ├── DEPLOYMENT.md
│   ├── FILE_MAP.md
│   ├── CHANGELOG.md
│   ├── SESSION_LOG.md
│   ├── RISKS_AND_OPEN_QUESTIONS.md
│   └── decisions/
│       └── ADR-0001-local-first-architecture.md
└── (application source code is introduced only after documentation approval)
```

Use sensible cross-links. Do not duplicate entire documents; link to the canonical source.

## 10. Required document contents

### `/AGENTS.md`
The mandatory agent entry point. Include:
- Required initialization reading order.
- Documentation-first workflow.
- Change/test/documentation checklist.
- Timestamp rules.
- Security and secret-handling rules.
- Rules against unsupported claims and quota circumvention.
- Definition of done.
- Instruction to inspect actual code and Git status.
- Instruction to update logs and project status.
- Instruction to stop and ask when a material product/security/cost decision is unresolved.

### `/README.md`
Include:
- Product summary.
- Current project status (planning, MVP, etc.).
- Goals and non-goals.
- High-level architecture.
- Current features versus planned features (never confuse them).
- Setup instructions once implementation exists.
- Test instructions once available.
- Documentation entry point.
- Security warning not to commit credentials.
- Project license status; do not assume a license without owner approval.

### `/docs/README.md`
This is the documentation map and second entry point. Tell new agents exactly which documents to read and in what order. Explain which document is canonical for each topic.

### `/docs/PRODUCT_REQUIREMENTS.md`
Include:
- Problem statement.
- Target users and use cases.
- Functional requirements with stable IDs such as `FR-001`.
- Non-functional requirements with IDs such as `NFR-001`.
- MVP scope and explicit exclusions.
- User journeys.
- Acceptance criteria.
- Constraints and assumptions.

### `/docs/IMPLEMENTATION_PLAN.md`
Include:
- Phases, task IDs, dependencies, acceptance criteria, and exit gates.
- A realistic milestone plan, not false precision about completion dates.
- Estimated effort as ranges and clearly labeled estimates.
- Required tests and docs for each phase.
- Current phase and next approved task.
- Do not silently mark tasks done; require evidence.

### `/docs/PROJECT_STATUS.md`
Include:
- Last updated timestamp.
- Current milestone.
- Implemented and verified items.
- Partially implemented items.
- Not started items.
- Current blockers.
- Latest test status.
- Risks needing attention.
- Next 1–3 recommended tasks.
- Link to the latest session-log entry.

### `/docs/ARCHITECTURE.md`
Include:
- System context and component diagram in Mermaid.
- Component responsibilities.
- Request lifecycle.
- Provider adapter boundary.
- Model catalog and routing relationship.
- Persistence approach.
- Security boundaries.
- Failure behavior.
- Local versus hosted deployment boundary.
- Architectural tradeoffs and known limitations.

### `/docs/DATA_MODEL.md`
Specify the initial SQLite entities and relationships, likely including:
- `providers`
- `provider_credentials` or secure credential references
- `models`
- `provider_models`
- `routing_profiles`
- `routing_rules`
- `request_events`
- `provider_health_events`
- `app_settings`

Do not store raw API keys in ordinary tables as plaintext. Choose a secure local credential-storage strategy after documenting platform constraints. If encrypted storage is unavailable or not yet implemented, document the limitation and keep the feature disabled rather than pretending it is secure.

Define fields, types, constraints, indexes, relationships, migration policy, and retention. Store only usage metadata needed for the MVP; do not persist prompts/responses by default.

### `/docs/API_SPECIFICATION.md`
Document the planned API routes, request/response schemas, authentication, status codes, errors, streaming behavior, and compatibility limitations.

Initial target routes:
- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`
- `GET /api/providers`
- `POST /api/providers`
- `PATCH /api/providers/{provider_id}`
- `DELETE /api/providers/{provider_id}`
- `GET /api/model-catalog`
- `POST /api/model-catalog/refresh`
- `GET /api/routing-profiles`
- `POST /api/routing-profiles`
- `PATCH /api/routing-profiles/{profile_id}`
- `GET /api/usage`
- `GET /api/events`
- `GET /api/settings`

These are proposed endpoints, not claims of existing implementation. Finalize exact schemas before coding. Do not expose secrets in GET responses.

### `/docs/MODEL_CATALOG.md`
Document:
- Model versus provider versus provider-specific model deployment.
- Discovery sources and supported official APIs.
- Refresh strategy, caching, freshness timestamp, and stale-data behavior.
- Capability metadata and how it is verified.
- Licensing and model terms metadata where available.
- Free-tier labels and how claims are verified.
- Difference between open weights, free hosted inference, and locally installed models.
- How users can add a custom compatible provider/model.
- How to handle removed, renamed, or unavailable models.

Never equate “open source/open weights” with “free hosted API.” Do not assume that a provider's advertised free access is unlimited. Avoid scraping or undocumented endpoints when an official integration is available.

### `/docs/ROUTING_AND_FAILOVER.md`
Document:
- Routing inputs and decision order.
- Explicit model versus `auto` model selection.
- Task profiles: coding, general chat, reasoning, and future multimodal categories.
- Capability filters: context, tool calling, streaming, vision, output modality.
- Provider health and temporary cooldowns.
- Error classification.
- Bounded retry budget and backoff.
- Failover before response content is streamed.
- Token/context estimation and uncertainty.
- Provider quota handling and `Retry-After` support when supplied.
- Duplicate request and request-ID considerations.
- Deterministic tests with mocked provider responses.
- Why the gateway cannot promise a fixed quantity of free tokens.

### `/docs/PROVIDER_INTEGRATIONS.md`
Document:
- Common adapter interface.
- Provider-specific configuration.
- Authentication and secret handling.
- Official documentation links.
- Model IDs and capability mapping.
- Usage metadata.
- Streaming and tool-calling differences.
- Error normalization.
- Rate limits and terms verification.
- Test fixtures and mock behavior.
- Steps to add a new provider without modifying core routing logic unnecessarily.

### `/docs/FRONTEND_SPECIFICATION.md`
Document:
- Framework and directory conventions after approval.
- Page map and navigation.
- Design principles, responsive behavior, accessibility, and loading/error/empty states.
- Dashboard overview.
- Model explorer and filters.
- Provider settings.
- Routing profile editor.
- Usage and event history.
- Form validation.
- API integration and state management.
- UI tests and screenshot/demo policy.
- Clear distinction between planned and implemented UI.

### `/docs/SECURITY_AND_PRIVACY.md`
Include:
- Threat model for a local service.
- API authentication for local clients.
- Host binding: bind to loopback by default, not `0.0.0.0`.
- CORS/CSRF considerations for a browser dashboard.
- Protection against DNS rebinding and unauthorized local requests.
- Credential storage and redaction.
- No secrets in source, logs, tests, screenshots, or Git.
- No prompt/response persistence by default.
- Data retention and deletion.
- Dependency vulnerability management.
- Safe remote access requirements.
- Provider terms and acceptable usage.
- Security testing and known limitations.
- Avoid logging raw prompts, API keys, authorization headers, or sensitive content.

### `/docs/TESTING_STRATEGY.md`
Include:
- Unit, integration, API contract, frontend, and end-to-end test layers.
- Mock providers; do not consume real quota in routine tests.
- Routing/failover test matrix.
- Rate limit, timeout, authentication, invalid response, context overflow, and provider outage cases.
- Streaming and partial-response failure cases.
- Capability mismatch cases.
- Database migration tests.
- Security tests.
- Lint/format/type-check/build commands once chosen.
- Definition of test evidence and reporting.

### `/docs/DEVELOPMENT_SETUP.md`
Include:
- Supported OS/runtime assumptions.
- Prerequisites.
- Installation and environment setup.
- `.env.example` usage.
- Local database setup.
- Running backend/frontend.
- Running tests and quality checks.
- Common errors and troubleshooting.
- Never include real secrets.

### `/docs/DEPLOYMENT.md`
For the MVP, focus on local development and safe local use. Document production and Docker plans as future work. Explain that the local API must not be exposed to a public network without authentication, transport security, access controls, and an explicit deployment review.

### `/docs/FILE_MAP.md`
Maintain a practical file/folder inventory. For each important module or directory, record its responsibility and links to related design documents. Update whenever files/folders are added, removed, moved, or their responsibilities materially change. Avoid listing every generated cache/build artifact.

### `/docs/CHANGELOG.md`
Use dated, timestamped entries with:
- Summary.
- Changed areas/files.
- User-visible or technical impact.
- Tests run and result.
- Links to related decisions/session log when useful.

Do not copy entire Git diffs into the changelog.

### `/docs/SESSION_LOG.md`
Append-only work-session log. Each entry should include:
- Start/end timestamps when known.
- Objective.
- Repository state/branch if relevant.
- Files changed.
- Decisions and rationale.
- Commands/tests run and actual results.
- Problems encountered.
- Next steps.

Do not rewrite previous entries except to correct a clear factual error; document corrections explicitly.

### `/docs/RISKS_AND_OPEN_QUESTIONS.md`
Track each issue with ID, description, probability/impact, mitigation, owner/decision needed, and status. Include uncertainty around provider quotas, catalog accuracy, credential storage, cross-provider API compatibility, local hardware performance, and future Android access.

### `/docs/decisions/ADR-0001-local-first-architecture.md`
Record why the MVP starts local-first, the alternatives considered, consequences, and what would justify revisiting the decision.

---

# PART D — FUNCTIONAL REQUIREMENTS

## 11. Model catalog and discovery

### MVP requirements
- Represent a model independently from a provider-specific deployment.
- Display model ID, provider, task capabilities, context limits where known, streaming/tool support where known, pricing/free-tier metadata where verified, and last-checked time.
- Allow manual refresh.
- Cache discovery data to avoid excessive provider calls.
- Show stale/unknown information explicitly.
- Allow the user to enable/disable a provider or deployment.
- Do not call every catalog entry “available” unless current eligibility is known.
- Keep local model inventory separate from hosted model catalog entries.

### Later requirements
- Scheduled refresh.
- Additional discovery integrations.
- Model recommendations based on task and constraints.
- Duplicate/canonical model identification.
- User-configurable custom compatible endpoints.

## 12. Provider management

- Users can add, edit, enable, disable, and remove a provider configuration.
- Validate configuration without exposing secrets.
- Support provider-specific credential requirements.
- Offer a “test connection” action with safe error messages.
- Store provider health and last successful check.
- Show quota information only when the provider exposes it or when the user explicitly supplies a value.
- Never infer exact remaining quota from request counts alone.
- Never silently use an unconfigured user's account or a shared key.

## 13. Routing engine

### Inputs
- Requested model or `auto`.
- Messages and estimated input size.
- Requested output token limit.
- Task profile.
- Tool definitions and tool-call history.
- Streaming requirement.
- Multimodal requirements.
- User priority policy.
- Enabled providers and known health state.

### Decision flow
1. Validate request shape.
2. Resolve requested model or routing profile.
3. Filter to models with the required capabilities.
4. Filter to configured, enabled, eligible deployments.
5. Respect user priority, constraints, and any cost preference.
6. Select a candidate.
7. Send request through its provider adapter.
8. Normalize response and usage metadata.
9. On a retryable failure, check retry budget and select an eligible alternative.
10. Record the final outcome and attempts without logging secrets or raw prompts.

### Retry/failover rules
- Never retry forever.
- Respect `Retry-After` if available and reasonable.
- Use exponential backoff with jitter for transient failures.
- Do not repeatedly retry authentication/permission failures.
- Treat invalid requests as client errors, not provider outages.
- Handle context-length failures as compatibility/size issues, not generic transient errors.
- Avoid retrying after a streamed response has started unless a safe protocol is designed.
- Avoid automatic fallback for explicitly requested models unless the API contract clearly tells the user fallback is enabled.
- Record why each candidate was rejected and why the final candidate was selected, while keeping logs free of sensitive prompt content.

## 14. API gateway and IDE compatibility

The MVP should provide a local OpenAI-compatible chat-completions interface for supported clients.

Requirements:
- `GET /v1/models`
- `POST /v1/chat/completions`
- Non-streaming responses.
- Streaming support added only after the non-streaming contract is tested.
- Normalized errors.
- Local authentication token configurable by the user.
- Clear documentation for configuring a compatible IDE.
- Explicitly document unsupported OpenAI API features and provider differences.

Do not claim “works with any IDE.” Say “works with IDEs and clients that support the documented compatible API and required features.”

## 15. Dashboard

Initial pages:
1. Overview.
2. Model Explorer.
3. Providers.
4. Routing Profiles.
5. Usage and Events.
6. Settings and Diagnostics.

Include:
- Accessible forms and labels.
- Loading, error, and empty states.
- Responsive layout.
- Confirmation for destructive actions.
- Clear secret-input handling.
- No fake usage statistics or fabricated model availability.
- Clear indicators for local versus hosted models.
- Clear labels for free-tier metadata and its verification time.

## 16. Usage and event logging

Capture minimal operational metadata:
- Request ID.
- Timestamp.
- Requested model/profile.
- Selected provider/model.
- Attempt count.
- Success/failure status.
- Normalized error category.
- Latency.
- Input/output token counts if provided.
- Whether a failover occurred and why.

Do not persist prompts or generated responses by default. If future debugging requires content capture, it must be optional, explicit, off by default, and documented with retention/deletion behavior.

---

# PART E — PROPOSED REPOSITORY STRUCTURE

Use this as the target structure after the documentation baseline is approved. Do not create all source files in the documentation-only phase.

```text
freeflow-ai/
├── AGENTS.md
├── README.md
├── .gitignore
├── .env.example
├── docs/
│   ├── ... documentation listed above ...
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   └── schemas/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── errors.py
│   │   │   └── logging.py
│   │   ├── catalog/
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   └── adapters/
│   │   ├── routing/
│   │   ├── usage/
│   │   ├── security/
│   │   └── storage/
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── contract/
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── overview/
│   │   │   ├── models/
│   │   │   ├── providers/
│   │   │   ├── routing/
│   │   │   └── usage/
│   │   ├── lib/
│   │   └── types/
│   └── tests/
├── scripts/
└── .github/
    └── workflows/
```

The exact frontend framework, dependency manager, database migration tool, and configuration strategy must be finalized in the documentation and ADRs before implementation. Avoid unnecessary abstraction layers for an MVP.

---

# PART F — PHASED IMPLEMENTATION PLAN

## Phase 0 — Repository audit and documentation baseline

**Status:** First task. No application implementation.

Tasks:
- Inspect existing repository and Git state.
- Create/update the mandatory documentation.
- Define requirements and architecture.
- Define initial API and data model.
- Record risks, assumptions, and open questions.
- Agree on technology choices.
- Review docs for consistency.

Exit criteria:
- All required documentation files exist.
- `AGENTS.md` contains the agent initialization protocol.
- Current project state is accurately documented.
- Major unresolved decisions are explicitly listed.
- Project owner has reviewed the documentation baseline.

## Phase 1 — Backend skeleton and local health

Tasks:
- Create the backend package and configuration.
- Add `GET /health`.
- Add local API authentication design/implementation.
- Add structured, redacted logging.
- Establish formatting, linting, typing, and test commands.
- Add a minimal automated CI workflow if approved.

Exit criteria:
- Backend starts locally using documented instructions.
- Health endpoint works.
- Configuration validation works.
- Secrets are not logged.
- Unit/API tests pass.

## Phase 2 — Provider abstraction and local inference

Tasks:
- Define a provider adapter protocol/interface.
- Implement a mock provider for deterministic tests.
- Add an Ollama adapter.
- Normalize provider errors and responses.
- Add connection testing and capability metadata.

Exit criteria:
- Requests can be routed to a local model.
- Mock tests cover success, timeout, invalid response, and unsupported capability.
- Provider logic is separate from API routes and core routing.

## Phase 3 — Hosted provider integrations

Tasks:
- Choose the first hosted providers based on official documentation and currently available user credentials.
- Implement adapters one at a time.
- Add safe credential configuration.
- Normalize usage metadata and provider errors.
- Document provider-specific limitations and terms.

Exit criteria:
- Each integration has mocked tests and an optional manual smoke-test procedure.
- Routine tests do not require real credentials or consume real quota.
- No secrets are committed.
- The dashboard accurately shows configured versus unconfigured providers.

## Phase 4 — Model catalog

Tasks:
- Create catalog schema and persistence.
- Add provider model discovery where official APIs support it.
- Add local Ollama model inventory.
- Add manual refresh and caching.
- Add capability and metadata normalization.
- Mark freshness and unknown fields.

Exit criteria:
- Models are discoverable from implemented sources.
- Stale and unknown data is clearly represented.
- A catalog entry is not automatically treated as an eligible inference target.

## Phase 5 — Routing and automatic failover

Tasks:
- Implement explicit model selection.
- Implement `auto` routing profile.
- Add capability filters.
- Add provider health and cooldown.
- Add retry budgets and backoff.
- Add rate-limit, timeout, authentication, context, and unsupported-feature classifications.
- Add structured routing-decision events.

Exit criteria:
- Deterministic tests demonstrate correct selection and fallback.
- No infinite retry loops.
- Non-retryable errors do not cause pointless failover.
- Streaming limitations are documented.
- Routing decisions are inspectable without exposing secrets or prompts.

## Phase 6 — OpenAI-compatible API

Tasks:
- Implement `GET /v1/models`.
- Implement `POST /v1/chat/completions`.
- Validate request and response schemas.
- Normalize errors.
- Add non-streaming support first.
- Add streaming only after contract tests and failure behavior are designed.
- Document IDE setup.

Exit criteria:
- A compatible API client can make a successful request through the gateway.
- API tests cover success and failure cases.
- Compatibility limits are documented.
- Local API is bound to loopback by default.

## Phase 7 — Dashboard

Tasks:
- Build overview.
- Build model explorer.
- Build provider management.
- Build routing profile editor.
- Build usage/event views.
- Add loading/error/empty states and validation.
- Add frontend tests.

Exit criteria:
- User can configure the system without editing database records manually.
- UI displays actual backend state, not hardcoded mock statistics.
- Sensitive values are never revealed in full after saving.
- Main flows work at common desktop sizes and are keyboard accessible.

## Phase 8 — Reliability, security, and usability

Tasks:
- Add database migrations and backup/reset guidance.
- Add abuse protection and request-size limits.
- Review CORS/CSRF and local browser security.
- Review logging and secret redaction.
- Test provider outages and malformed responses.
- Improve troubleshooting and diagnostics.
- Review dependencies.

Exit criteria:
- Security review findings are documented and addressed or explicitly deferred.
- Failure behavior is predictable.
- Setup and troubleshooting docs match the implementation.

## Phase 9 — Packaging and portfolio release

Tasks:
- Add reproducible installation instructions.
- Add Docker support only where useful for local deployment.
- Add CI tests and lint/type checks.
- Add architecture and demo diagrams.
- Add sample configuration with placeholders.
- Record a demo plan and known limitations.
- Choose an open-source license only with project-owner approval.

Exit criteria:
- A fresh checkout can be set up using the README.
- CI runs the documented checks.
- Demo can be reproduced without committing secrets.
- Portfolio claims are supported by test or demo evidence.

## Phase 10 — Later roadmap

Not part of the MVP:
- Android control app.
- Secure gateway pairing between Android and desktop.
- Optional remote access with authentication and transport security.
- Additional hosted providers.
- Image-generation/audio-specific adapters.
- More sophisticated routing based on measured latency and user-configured cost preferences.
- Optional cloud deployment, only after a separate security/cost review.
- Optional opt-in prompt capture for debugging, only after privacy review.

---

# PART G — INITIAL TEST MATRIX

Use mock adapters for repeatable tests.

| Scenario | Expected result |
|---|---|
| Preferred provider succeeds | Return its normalized response |
| Preferred provider rate-limits | Respect retry guidance or select eligible alternative |
| Preferred provider times out | Retry/fail over within configured budget |
| Invalid API key | Report authentication error; do not retry endlessly |
| All providers fail | Return normalized failure and record attempts |
| Explicit model unavailable | Return a clear error unless explicit fallback policy allows otherwise |
| Auto mode, text request | Select an eligible text-capable deployment |
| Auto mode, image input | Exclude deployments without vision support |
| Context too large | Reject clearly or select a compatible model; do not loop |
| Tool calls requested | Use only a deployment whose support is verified |
| Provider returns malformed JSON | Normalize error and record failure |
| Provider returns usage metadata | Store token counts if present |
| Provider omits usage metadata | Mark usage as unavailable/unknown, not zero |
| Streaming disconnect before first token | Apply safe retry policy if possible |
| Streaming disconnect after output begins | Avoid blind provider switching that duplicates output |
| API key is configured | Redact it in logs and API responses |
| Dashboard loads with no providers | Show an empty state, not fabricated data |
| Catalog refresh fails | Keep prior cached data and mark it stale |
| Local model is unavailable | Report it and select another eligible backend if policy permits |

---

# PART H — ACCEPTANCE CRITERIA FOR THE FIRST PUBLIC MVP

The public MVP should not be considered ready until:

1. A user can run the gateway locally using documented instructions.
2. The dashboard shows configured providers and catalog models accurately.
3. At least one local provider and two hosted provider adapters are implemented and tested, subject to credentials and current provider terms.
4. The user can make a request through one stable API endpoint.
5. Automatic failover is bounded, capability-aware, and covered by deterministic tests.
6. An IDE/client that supports the documented API can use the gateway.
7. Request metadata, latency, usage when available, and failover events are inspectable.
8. Provider credentials are not committed, logged, or returned by configuration endpoints.
9. The service binds to loopback by default.
10. Setup, architecture, API, security, and troubleshooting documentation matches actual behavior.
11. Automated checks pass, with actual results recorded.
12. The README clearly states limitations and does not promise unlimited tokens or universal IDE compatibility.

---

# PART I — CURSOR EXECUTION PROMPT

After reviewing the instructions above, follow this exact first-pass task:

> **Task: Perform a repository audit and establish the documentation baseline for FreeFlow AI. Do not implement application features yet.**
>
> 1. Inspect the current repository and Git status without destructive changes.
> 2. Read any existing project instructions and preserve useful existing work.
> 3. Create/update `AGENTS.md` as the mandatory onboarding and documentation-governance entry point.
> 4. Create/update the documentation files and content specified in this plan.
> 5. Make sure `docs/README.md` gives every future AI agent a precise document-reading order.
> 6. Make sure `docs/PROJECT_STATUS.md` accurately reflects the repository's real current state.
> 7. Add the timestamped documentation baseline entry to `docs/CHANGELOG.md` and `docs/SESSION_LOG.md`, using the actual current Asia/Kolkata timestamp.
> 8. Add an initial architecture decision record for local-first architecture.
> 9. Check all internal links, consistency between requirements and architecture, and whether proposed features are clearly labeled as planned rather than implemented.
> 10. Do not add backend/frontend application source code in this first pass. Do not install dependencies, add paid services, create accounts, or call provider APIs.
> 11. Provide a concise final report: repository state found, documents created/updated, decisions proposed, unresolved questions, and the next recommended implementation task.
> 12. Stop and wait for the project owner's approval before beginning Phase 1.
>
> For all later tasks, follow `AGENTS.md`. Before each change, state the intended files and tests; after each change, update relevant documentation, changelog, session log, project status, and file map as applicable. Never claim checks passed unless they were actually run.

---

# PART J — PROJECT OWNER REVIEW CHECKLIST

Before approving implementation, confirm:

- [ ] The product remains local-first for the MVP.
- [ ] The initial UI is a web dashboard, not the Android app.
- [ ] The gateway uses user-owned provider credentials.
- [ ] Open-weight models and free hosted inference are treated as distinct concepts.
- [ ] The router respects provider quotas and terms.
- [ ] The MVP begins with text chat and expands capabilities through adapters.
- [ ] Provider integrations are selected based on current official documentation.
- [ ] Secrets are handled securely and never committed.
- [ ] `AGENTS.md` is the required entry point for every future agent.
- [ ] All meaningful changes require tests and documentation updates.
- [ ] Changelog and session logs use real timestamps in Asia/Kolkata.
- [ ] The documentation baseline is reviewed before implementation starts.

**End of plan.**
