# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Three equally weighted audiences:

1. **Solo developer on Windows** — wants a single local API endpoint that routes to multiple AI providers (local and hosted) so their IDE or scripts need only one configuration.
2. **Learner / portfolio engineer** — building a documented, testable system that demonstrates real routing, adapter design, and operational transparency as a portfolio project.
3. **Ollama power user** — wants local-only AI operation when a compatible local model is installed, without mandatory cloud dependencies.

All users are a single trusted local operator on their own machine. No multi-tenant, team, or admin personas in the MVP.

## Product Purpose

FreeFlow AI is a local-first, provider-agnostic AI gateway. It gives the user one local HTTP endpoint that can route requests to configured hosted AI providers or local inference runtimes (starting with Ollama). A web dashboard on the same machine lets the user manage providers, explore model catalogs, configure routing profiles, and inspect request events — without editing config files or databases by hand.

Success means: the user can install it, point it at their providers, and have a working OpenAI-compatible chat completions endpoint with honest visibility into what happened and why.

## Positioning

Two differentiators the user actually experiences:

1. **Portfolio-grade transparency** — every routing decision is inspectable. Model capabilities, availability, and free-tier status are reported honestly; unknowns are labeled unknown, not zero. No fabricated usage, fake availability, or "unlimited free tokens" claims.
2. **Unified local + hosted routing with real failover** — not a proxy. The gateway selects, retries, and fails over across providers within bounded budgets, with capability filtering and health tracking. Local and hosted models participate in the same routing policy.

## Operating Context

- Runs on the user's Windows machine (initial target OS). Other OS support is later.
- Backend binds to `127.0.0.1` by default — the gateway is not exposed to the network.
- Users bring their own provider API keys. No shared credentials, no FreeFlow cloud account.
- Compatible clients (IDEs, HTTP tools) call the local OpenAI-compatible endpoint.
- Dashboard is accessed in the user's browser at the local URL.
- SQLite stores operational metadata (settings, catalog cache, events). Prompts and responses are not persisted by default.
- Ollama (or compatible local runtime) runs alongside when local models are wanted.

## Capabilities and Constraints

**Confirmed capabilities (MVP scope):**

- `GET /health` (unauthenticated), `GET /v1/models`, `POST /v1/chat/completions` (non-streaming first).
- Bearer token authentication for all routes except health.
- Provider adapters: mock provider, Ollama, and at least two hosted providers (chosen after official-docs review; subject to owner having credentials).
- Model catalog with discovery, caching, freshness timestamps, capability metadata, and stale labeling.
- Routing engine with explicit model selection, `auto` routing profiles, capability filters, health/cooldown, bounded retry with backoff.
- Dashboard pages: Overview, Model Explorer, Providers, Routing Profiles, Usage & Events, Settings & Diagnostics.
- Structured, redacted logging (secrets never in logs).
- Deterministic test suite using mock providers — routine tests never consume real quota.

**Constraints:**

- Product name is provisional — do not rename identifiers without owner approval.
- License is unchosen (OQ-001). No open-source license can be assumed.
- OpenAI-compatible surface is a documented subset, not full compatibility.
- Streaming lands only after non-streaming is tested.
- Tool calling, vision, JSON mode, embeddings are out of the first slice unless an adapter ships with tests.
- Credential storage design must precede implementation — features stay disabled rather than storing plaintext.
- No multi-user, billing, subscriptions, remote access, or cloud-hosted service in MVP.

**Undecided:**

- Frontend framework is proposed (React + TypeScript + Vite) but not formally confirmed (OQ-003).
- Windows credential-storage approach for API keys (OQ-005).
- First hosted providers not yet selected (OQ-004).

## Evidence on Hand

- Complete documentation system in `docs/` (requirements, architecture, API spec, data model, routing, providers, frontend spec, security, testing strategy, deployment).
- Working backend skeleton: FastAPI app with health endpoint, Bearer auth, structured logging with secret redaction.
- 18 passing tests (health, auth, logging/redaction).
- Quality tooling configured: ruff, mypy, pytest — all clean.
- No frontend code, no dashboard, no visual assets, no logo, no brand guidelines.
- No real provider adapters yet (mock provider is Phase 2).

## Product Principles

1. **Honest by default** — show what is actually known. Label unknowns, stale data, and missing capabilities. Never fabricate availability, usage, or model support.
2. **Local-first, user-controlled** — the gateway runs on the user's machine, credentials stay under user control, and no cloud account is required.
3. **Inspectable routing** — every routing decision, failover, and failure is visible and traceable through events, without exposing secrets or prompt content.
4. **Test what you ship** — features land with tests, docs update in the same cycle, and quality checks pass before completion is claimed.
5. **Small, reviewable increments** — work in phases with exit gates, not big-bang releases.

## Accessibility & Inclusion

Dashboard must be keyboard accessible for main flows, with semantic headings/landmarks, sufficient contrast for text and status indicators, and color not used as the only status signal. Desktop-first, but readable at 1280px and 768px widths.
