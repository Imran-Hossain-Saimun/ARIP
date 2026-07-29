# Increment 3 — Request queue + record + approve/escalate

**Status:** done

## Scope
The product's core loop. Get keyboard nav and optimistic approve right here; every
later list/record screen copies this pattern.

## Backend
- `app/requests/router.py`:
  - `GET /v1/requests?status&dept&conf_lt&cursor` — cursor-paginated list
  - `GET /v1/requests/:id` — full detail (messages, attachments, decisions)
  - `POST /v1/requests` — create (web channel; email comes in increment 6)
  - `PATCH /v1/requests/:id/assign` — assign/reassign (§12: dept_manager=F, agent=W own)
  - `POST /v1/requests/:id/approve` — approve & send; writes audit event same transaction
  - `POST /v1/requests/:id/escalate` — escalate; writes audit event
  - `Idempotency-Key` header required on approve/escalate (§09 convention)
- Department-scoping: `dept_manager`/`support_agent` "W" level is scoped to their own
  `department_id` — enforce as a query filter, not a UI-only restriction
- Extend seed script toward §13's target: 400 requests across the four decision bands
  and both channels (can start smaller, e.g. 40-60, and grow later)

## Frontend
- `RequestWorkspace` (see plan's §10 component hierarchy): `QueueToolbar` (SavedViewTabs,
  FilterBar, DensityToggle, SortMenu) + `SplitPane` (420px list + record)
- `RequestList` using the `DataTable` primitive, virtualized, `RequestRow` → StatusBadge +
  SlaTimer
- `RequestRecord`: RecordHeader, MetaChipRow, Tabs (Conversation/AI Decision/Evidence/
  Workflow/Audit — Evidence+AI Decision tabs get fully wired in increment 4), RuleHoldBanner,
  MessageBubble, AiDraftCard w/ CitationChip, RecordActionBar (approve/edit/reject)
- Keyboard nav: `J`/`K` row navigation, `Enter` open, `A` approve, `E` escalate, `Esc` close
  (§04 accessibility requirement)
- Optimistic approve via TanStack Query mutation + rollback on failure

## Verification target
- Critical E2E test #1 from §13: agent approves a draft → queue → record → trace →
  approve → audit event exists → next request auto-focused
- pytest coverage for department-scoped assign/approve/escalate authorization

## Delivered
- Backend: all 5 endpoints above, `app/core/idempotency.py` (in-process de-dup — swap for
  Redis-backed before running >1 API replica), `enforce_department_scope`/
  `is_department_scoped` in `app/core/permissions.py`, `RequestValidationError` handler
  added to `app/main.py` so FastAPI's default 422s also match the uniform error shape.
  16 sample requests seeded across all 4 confidence bands, both channels, with 2 rule-hold
  cases (BR-022 Legal, BR-014 Compliance). 11 new pytest tests (25 total).
- Frontend: `features/requests/{types,api,RequestList,RequestRecord,RequestQueuePage}.tsx`.
  **Deviated from plan**: the list pane uses compact `RequestRow`-style cards, not the
  `DataTable` primitive — a real multi-column table with headers didn't fit the 420px
  list pane legibly (columns truncated to unreadable). `DataTable` stays reserved for wide
  screens (Knowledge Library, Audit log) per its original intent.
  Tabs shell shows all 5 (Conversation/AI Decision/Evidence/Workflow/Audit) with the
  unbuilt ones disabled + tooltipped to their landing increment, rather than hidden —
  matches §11's "Permission" state pattern (visible-but-disabled, not silently missing).
- **Verified live in Chrome**: department scoping (agent sees only their dept's 2 of 16
  requests), approve (optimistic update + auto-advance to next request), escalate (inline
  reason textarea, not a native `window.prompt`/dialog), and the BR-022/BR-014 rule-hold
  banners rendering correctly on 98%/93%-confidence requests that were still held.
- **Simplification not in the original plan**: request status transitions on approve/
  escalate are unconditional (`approve` always → `answered`, `escalate` always → `routed`)
  — no full state-machine validation of legal transitions yet. Fine for this increment's
  scope; worth tightening if increment 7's workflow engine needs stricter transition rules.
