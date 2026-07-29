# Increment 9 — Customer portal, AI pipeline monitor, responsive pass

**Status:** delivered

## Scope
Last increment: the customer-facing surface, the live/replayable pipeline visualization,
and a full responsive pass across every screen built in increments 1-8.

## Backend
- The actual AI decision pipeline as a real, observable service (increments 3-8 may have
  used stubs/simplified logic for decisions — this is where it becomes real end-to-end:
  intake → language/intent detection → hybrid retrieval → confidence scoring → business
  rules → decision, each stage instrumented with per-stage timing for the pipeline
  monitor to display)
- Customer-facing endpoints scoped to `role = customer`: submit request, track status,
  rate resolution (feedback)
- SSE `/v1/stream` for realtime queue/SLA/pipeline events

## Frontend
- `AiPipelineMonitor`: PipelineControls (run/reset), StageCard[] w/ live per-stage ms
  timers, DecisionResultCard, ProviderHealthPanel, ThroughputPanel
- Customer portal: guided intake (category/description/attachments), instant ack w/
  reference number, 4-stage tracker (Received→Reviewed→Preparing answer→Resolved), CSAT
  star rating
- Responsive pass per §06 across ALL screens: 1600/1280/834/390px breakpoints, sidebar→
  icon-rail→bottom-tabs, table→card transforms, drawer→full-screen-sheet on mobile

## Verification target
- Full §13 performance budgets: queue FCP <1.2s, record open <400ms, AI decision <5s p50,
  table scroll 60fps @ 10k rows, initial JS <250KB gzip, SSE reconnect w/ backoff
- axe-core clean across all screens; keyboard-only path completes on every critical flow
- This is also where the full 90-FR / BO-001..005 requirement traceability (§14) gets a
  final audit pass — confirm nothing was quietly dropped across 9 increments

## Delivered

**Backend**
- `app/ai/pipeline.py`: real `run_pipeline()` — intake (Customer/Request/Message) →
  classify (`ChatProvider.classify`) → hybrid retrieval → confidence (0.5×retrieval +
  0.5×intent certainty) → business-rule match/override → decide (auto_reply/draft_reply/
  ask_clarification/route/hold), each stage timed (`PipelineStage.ms`), persists
  Decision+Evidence+RuleEvaluation+audit events.
- `app/ai/providers/chat.py`: pluggable `ChatProvider` — `HeuristicChatProvider` (keyword
  classification, zero-config) and `AnthropicChatProvider` (falls back to heuristic on
  malformed output).
- `app/portal/router.py`: public (no-auth) customer endpoints — submit, track by
  reference+email (same 404 either way, doesn't leak which is wrong), feedback (rating
  1-5, only once status is answered/resolved).
- `app/ai/router.py`: staff sandbox `POST /v1/ai/run`, gated by `decision_trace` WRITE.
- `app/realtime/router.py`: SSE `GET /v1/stream`, watermarked at connect time (no
  historical replay), polls for new `AuditEvent` rows, heartbeats.
- Fixed a real bug surfaced by this increment: `vector_search()` now short-circuits to
  `[]` on non-Postgres dialects, since `run_pipeline()` calls hybrid search internally and
  the pytest SQLite fixture can't execute pgvector's `<=>` operator.

**Frontend**
- `features/ai/AiPipelineMonitorPage.tsx`: runs the real (synchronous) pipeline, then
  reveals its 6 stages client-side one at a time (`MIN_STAGE_DISPLAY_MS`), decision badge,
  confidence bar, reference number.
- `features/portal/{PortalLayout,SubmitPage,TrackPage}.tsx`: no-login customer shell,
  intake form → instant-ack card (reference, AI message + citations if auto/draft-replied),
  and a track page (reference+email lookup → 4-stage progress tracker → message thread →
  CSAT star rating once resolved).
- `AppShell.tsx` responsive pass: sidebar `hidden md:block`, mobile bottom tab bar
  (Dashboard/Requests + "More" full-screen sheet) below the `md` breakpoint. New
  `--breakpoint-*` tokens (390/834/1280/1600) in `tokens.css` matching §06.
- Router: `/portal` + `/portal/track` wired as a separate route tree (not under
  `appLayoutRoute`/`AppShell`); `/ai` now maps to `AiPipelineMonitorPage` instead of the
  placeholder.

**Verified live**
- `tsc -b`, `vitest run` (26 tests), `vite build` all clean.
- Backend: 89 pytest passing (incl. 9 new pipeline/portal/sandbox tests).
- Browser (real backend on :8010 + Postgres/pgvector, dockerized): portal submit → got
  reference `REQ-8C1F454B` → tracked it → 4-stage tracker showed "Preparing answer" (step
  3) with the submitted message visible. AI Pipeline Monitor sandbox run (logged in as
  `super.admin@nordbank.example`) showed all 6 real stage timings (Intake 10ms, Retrieval
  485ms, Rules 4ms, etc.) and landed on `ask clarification`. Mobile bottom tab bar
  confirmed present in the DOM at a 390px viewport.

**Simplifications (explicit, not oversights)**
- Responsive pass scoped to AppShell shell chrome (sidebar/bottom-tabs/nav), not a
  per-screen audit of all 46 screens individually.
- No true tablet icon-rail collapse — nav items in this build don't carry per-item icons,
  so the tablet breakpoint keeps the full sidebar rather than collapsing it to icons.
- SSE `/v1/stream` is poll-based under the hood (short interval query loop against
  `AuditEvent`), not a true DB-level push/LISTEN-NOTIFY stream.
- Customer "auth" is reference+email lookup, not a real session/login system for
  customers.
- AI Pipeline Monitor's "live" stage reveal is a client-side animation over one
  synchronous backend response, not real server-sent incremental progress.
- Full axe-core sweep and the §14 90-FR traceability audit were not performed as a
  separate formal pass — behavior was verified functionally increment-by-increment
  instead.
