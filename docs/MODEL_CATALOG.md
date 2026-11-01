# Model catalog

**Last updated:** 2026-10-31T22:30:00+05:30  
**Status:** Unified in-memory Model Catalog service (`backend/catalog/`) implemented and verified. Models identified unambiguously by composite IDs (`<provider_id>:<model_id>`). SQLite persistence pending.

---

## Concepts

| Term | Meaning |
|---|---|
| Model | Logical model identity (`models` table / `model_id`). |
| Provider | Configured backend (`ollama`, hosted adapter, `mock`). |
| Composite ID | `<provider_id>:<model_id>` ensuring unambiguous identification. |
| Catalog presence | We have an aggregated catalog row (`CatalogEntry`). |
| Eligibility | Configured + enabled + capable + allowed by health/policy. |

Never equate catalog presence with “this user can call it now.”

Never equate **open weights** with **free hosted inference**. Never equate **locally installed** with **hosted API**.

---

## Discovery sources

Use official APIs only. Do not scrape HTML or undocumented endpoints when an official integration exists.

| Source | What it yields | Status | Notes |
|---|---|---|---|
| Mock adapter | Fixture models | **Verified** | Tests only |
| Ollama list API (`/api/tags`) | Local inventory | **Verified** | Marked `is_local=True` |
| Hosted list-models APIs | Hosted catalog | Planned Phase 3 | Per adapter, after official-docs check |
| Manual entry | Custom compatible endpoint | Planned Phase 4 | User-supplied; capabilities often unknown |

First hosted sources are **not chosen** (OQ-004). When chosen, this table gets official documentation URLs.

---

## Refresh strategy

- **Manual refresh:** `POST /api/model-catalog/refresh` (proposed).
- **Scheduled refresh:** later (FR-026).
- Cache rows in SQLite. Store `last_checked_at` / `last_seen_at`.
- On refresh failure: **keep prior rows**, set `stale=1`, surface the error in diagnostics.
- Rate-limit refresh to avoid hammering providers.
- Routine automated tests must not call real list-models APIs.

---

## Capability metadata

Fields (boolean or unknown): text, vision, tools, streaming, context length, max output.

Verification levels:

1. **Adapter-asserted** from official model cards or API fields.
2. **User-asserted** for custom endpoints (label as user-asserted).
3. **Unknown** — do not guess; routing must not send incompatible payloads.

Do not probe live paid APIs in a loop to “discover” capabilities.

---

## Licensing and terms

Where official metadata exists, store a license/terms URL or SPDX-like label in `extra_json` / dedicated fields later. Do not invent licenses for third-party models.

---

## Free-tier labels

- Allowed: “provider documents a free tier as of `<verified_at>`” with a link to the official page.
- Forbidden: “unlimited free tokens,” implied remaining quota from our request counts, copying another site’s unofficial quota table.
- Free-tier status can change; UI must show verification time.

---

## Custom compatible providers

Users may add an OpenAI-compatible base URL and model ID. Required:

- User-owned credential.
- Capabilities default to unknown unless the user sets them.
- Routing treats unknown conservatively (text-only assumption only if we explicitly document that default — proposed default: unknown means **exclude** from auto vision/tool routes).

---

## Removed, renamed, or unavailable models

- If a model disappears from discovery: keep row, mark stale/unavailable, do not auto-delete events history.
- If renamed: new `provider_model_id`; old row marked unavailable.
- Explicit user request for a missing model: clear error unless fallback policy is enabled for that profile.

---

## Local versus hosted in the UI

Local inventory and hosted catalog must be visually and structurally distinct (`is_local`). A GGUF on disk is not a Groq-hosted model even if names look similar.
