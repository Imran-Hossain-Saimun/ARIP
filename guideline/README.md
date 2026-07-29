# ARIP — Implementation Guideline

This directory is the technical reference for how ARIP actually works today, with exact
`file:line` citations into `backend/` and `frontend/`. It's written for a developer or QA
engineer joining the project who needs to understand real behavior, not the aspirational
spec in `project/ARIP Design.dc.html`. Where the two disagree, this guideline describes
**what the code does**, and calls out the gap explicitly.

For build history (what was delivered in which increment, what was verified live), see
`tasks/*.md`. For the original architecture plan, see
`C:\Users\saimun\.claude\plans\wise-hugging-scott.md`. This directory is a different
thing: a standing reference to the *logic*, not a changelog.

## Documents

| # | File | Covers |
|---|------|--------|
| 0 | [00-setup.md](00-setup.md) | Local setup from a clean clone — infra, backend, frontend, seed data, running tests, every command actually verified |
| 1 | [01-request-lifecycle.md](01-request-lifecycle.md) | Request/Decision data model, every way a Request gets created, requests/decisions/portal API surface, approve/escalate/assign, idempotency, department scoping, realtime SSE |
| 2 | [02-knowledge-and-retrieval.md](02-knowledge-and-retrieval.md) | Document ingestion (chunking/hierarchy/embedding), the draft→approve→index lifecycle, hybrid retrieval (vector + keyword + RRF fusion), knowledge gaps |
| 3 | [03-ai-pipeline-and-llm-providers.md](03-ai-pipeline-and-llm-providers.md) | `run_pipeline()` stage-by-stage, confidence formula, business-rule override, every LLM/embedding call site, provider selection (Anthropic/OpenRouter/OpenAI/heuristic fallbacks) |
| 4 | [04-email-processing.md](04-email-processing.md) | How inbound email is polled from Mailhog, thread correlation, parse-failure triage — **and the real gap**: email is not connected to the AI pipeline or to any real mailbox/outbound SMTP today |
| 5 | [05-automation-versioned-config.md](05-automation-versioned-config.md) | The one shared `ConfigResource` draft→active→archived lifecycle reused by workflows/routing/business rules/prompts, and the rule simulator |
| 6 | [06-rbac-and-audit.md](06-rbac-and-audit.md) | The full §12 permission matrix as data, `assert_permission`/`require_permission`, department scoping, the sha256 hash-chained audit trail and its verify logic |
| 7 | [07-frontend-backend-map.md](07-frontend-backend-map.md) | Every frontend route → page → permission module → backing API calls; how auth/JWT and the API client work end to end |

## The request lifecycle in one paragraph

A request enters ARIP one of three ways: a customer submits it through the public
**portal** (`POST /v1/portal/requests`), an email lands in a **Mailhog-polled mailbox**
and gets synced in, or staff create one directly via the internal API. Only the portal
path runs the real AI pipeline synchronously — email-sourced and directly-created
requests are **not** automatically classified (see
[04-email-processing.md](04-email-processing.md) §5 and
[01-request-lifecycle.md](01-request-lifecycle.md) §3). The AI pipeline
(`backend/app/ai/pipeline.py:run_pipeline`) classifies the request, runs hybrid
retrieval against approved knowledge, scores confidence, checks for an overriding
business rule, and lands on a decision: auto-reply, draft-reply, ask-clarification,
route, or hold. Every mutation writes a hash-chained audit event
(`backend/app/core/audit.py`), and every read/write endpoint is gated by the same
role/action matrix (`backend/app/core/permissions.py`).

## What's real vs. simplified — the honest summary

Every module doc below has its own "known limitations" section with exact citations, but
if you only read one paragraph, read this one:

- **Email is a dead end for automation.** Mailhog polling, subject-based thread
  correlation, and parse-failure triage are real and tested — but no code path ever calls
  `run_pipeline()` for an email-sourced request, there's no real IMAP/Graph connector, and
  there's no outbound SMTP send anywhere in `app/`. See
  [04-email-processing.md](04-email-processing.md).
- **Knowledge retrieval quality depends entirely on `OPENAI_API_KEY`.** Without it,
  embeddings fall back to a deterministic-but-meaningless hash (real pgvector
  storage/query mechanics, fake semantics). OpenRouter can substitute for classification
  but not embeddings. See [02-knowledge-and-retrieval.md](02-knowledge-and-retrieval.md)
  and [03-ai-pipeline-and-llm-providers.md](03-ai-pipeline-and-llm-providers.md).
- **Decision replay is a stub.** `POST /v1/decisions/{id}/replay` only validates the
  decision exists — it does not re-run the pipeline. See
  [01-request-lifecycle.md](01-request-lifecycle.md) §5.
- **Workflows don't execute.** `WorkflowRun`/`WorkflowAction` are bookkeeping tables with
  no live execution engine reacting to decisions. See
  [05-automation-versioned-config.md](05-automation-versioned-config.md) §6.
- **Idempotency keys are in-process, no TTL.** Fine for one API process, not for multiple
  replicas. See [01-request-lifecycle.md](01-request-lifecycle.md) §6.
- **Realtime is polling, not push.** SSE polls the audit table every 2s and closes after
  ~2 minutes, relying on the browser's `EventSource` auto-reconnect. See
  [01-request-lifecycle.md](01-request-lifecycle.md) §9.
- **Knowledge gaps are never auto-created.** The `KnowledgeGap` model/status lifecycle
  exists, but nothing in the runtime path inserts or updates a gap row except the demo
  seed script. See [02-knowledge-and-retrieval.md](02-knowledge-and-retrieval.md) §6.

None of these are bugs to "fix" reflexively — they're documented, deliberate build
decisions (see each `tasks/NN-*.md` for the reasoning). They're listed here so a new
developer or QA engineer doesn't assume spec-complete behavior that isn't there.
