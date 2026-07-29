# Increment 8 — Analytics, audit log, admin, settings

**Status:** done — verified live in Chrome

## Scope
Insight and Configure nav groups. Executive/Auditor/Admin-facing surfaces.

## Backend
- `GET /v1/analytics/kpis?range` — BO-001..BO-005 targets from the BRD (manual-effort
  reduction ≥70%, routing accuracy ≥95%, first-response time, knowledge reuse, CSAT),
  automation funnel, most-cited knowledge
- `GET /v1/audit?type&actor&object&from&to` — query the existing hash-chained
  `AuditEvent` table (already built in increment 2); add an export endpoint (signed)
- Admin CRUD beyond the increment-2 read-only departments list: full Users/Roles/
  Departments CRUD, org settings, SSO config stub
- Settings: AI provider config (Anthropic/OpenAI keys + fallback chain), retrieval config
  knobs (chunk_size, overlap, vector_top_k, vectorless_depth, fusion strategy, min_score,
  rerank toggle — these were shown as concrete defaults in the prototype: 800/120/8/3/
  reciprocal_rank/0.62/enabled), mailbox connections, webhooks, API keys

## Frontend
- `AnalyticsDashboard`: DateRangePicker, ExportMenu, KpiTile[] vs BO targets (trend not
  snapshot per persona design response), FunnelChart, BarList, chart a11y fallback table
- Audit log stream (append-only, scroll/paginate), trace-by-request lookup
- Admin: Users/Roles/Departments tables, org settings, AI config tabs
- Settings screens for the retrieval/provider knobs above

## Verification target
- Critical E2E test #4 from §13: Executive deep-linking to `/rules` gets AccessDenied +
  a logged access-request audit event (permission check + audit-on-denial, not just on
  success)
- Exported audit log hash-chain verifies (each row's `prev_hash` matches the prior row's
  `hash`)

## Delivered
- **§13 E2E test #4, done properly**: `assert_permission`/`require_permission` (shared
  by every module in the app, not just this increment) now write an `access.denied`
  audit event — with actor, the denied module, and the attempted action — before raising
  the 403. This is retroactive: every prior increment's RBAC gate gained audit-on-denial
  for free since they all route through the same shared function.
- Backend: `GET /v1/analytics/kpis?range=N` computes all 5 BO KPIs from real
  Decision/Request/Evidence/Feedback data (no mocked numbers) — automation rate,
  a routing-accuracy proxy, real first-response-time (correlated subquery: first non-
  customer Message per Request), citation count, average CSAT — plus a decision-type
  funnel and top-5 most-cited-articles, all as real GROUP BY queries. `app/core/audit.py`
  gained `verify_chain()` (walks every event in order, recomputes each hash, returns
  where/if it breaks) exposed via `GET /v1/audit/verify` and `GET /v1/audit/export`.
  `app/admin/router.py` extended with `POST /departments`, `GET/POST/PATCH /users`.
  New `AppSetting` key-value table + `GET/PUT /v1/settings/:key` seeded with the exact
  retrieval defaults named in the spec (800/120/8/3/reciprocal_rank/0.62/enabled). 26 new
  pytest tests (80 total, plus the audit-on-denial fix covered by a new test in
  `test_permissions.py`).
- Seed script: added `Feedback` rows (rating 5 for auto-replied requests, 4 for approved
  drafts) so BO-005 (CSAT) has real data to average.
- Frontend: `AnalyticsPage` (KPI tiles with target coloring, funnel bar chart, most-cited
  list), `AuditLogPage` (filterable stream + a working "Verify chain" button), `AdminPage`
  (Users `DataTable` with an active/inactive toggle + create-user modal, Departments grid
  + create form), `SettingsPage` (JSON-edit cards per setting key — same "raw JSON"
  simplification as increment 7's automation config, for the same reason).
- **Verified live in Chrome**: Analytics showed real computed KPIs (29% automation rate
  correctly below the 70% target and colored accordingly, 5/5 CSAT from the seeded
  feedback, a populated funnel and most-cited list); Audit Logs showed the real seeded
  event stream and "Verify chain" reported "all 45 events form an unbroken hash chain";
  Administration listed all 7 seeded users in a real table with a working deactivate/
  reactivate toggle, and all 8 departments; Settings showed the exact spec-default
  retrieval knobs. No console errors.
- **Simplifications, clearly scoped down from the plan**:
  - BO-002 (routing accuracy) has no ground-truth "was this the right department"
    signal in the data model, so it's a proxy (share of decisions NOT routed to a human)
    rather than a true accuracy measure — documented in the endpoint's own docstring.
  - Settings are edited as raw JSON per key, not dedicated form UIs per provider/knob
    (same rationale as increment 7).
  - No SSO config stub, no webhook/API-key management UI — `AppSetting` could hold these
    as additional keys later but nothing was built for them this pass.
  - Roles are still the static enum from increment 2, not a dynamic roles/permissions
    table — "Roles" in the nav conceptually maps to the fixed §12 matrix, not an editable
    CRUD resource.
