# Increment 11 — Role-adaptive dashboard

**Status:** done — verified live in Chrome

## Why
`/` (Dashboard, nav item in `frontend/src/lib/rbac.ts:87`) was never assigned to any of
increments 1–10. `frontend/src/app/router.tsx:39-41,112-119` has no `REAL_PAGES['/']`
entry, so every role hits the generic `ModulePlaceholder` stub. Spec calls for 5 role
variants at this route (`project/ARIP Design.dc.html:210,722`: Agent, Manager, Knowledge
Manager, Executive, Auditor) — this increment builds it.

## Scope
Operations nav group, `/` route only. One backend endpoint, one frontend page with
role-conditional tile sets. No new tables — composes existing Decision/Request/Evidence/
AuditEvent data already queried by increments 3, 5, 8.

## Backend
- `GET /v1/dashboard/summary` (`app/dashboard/router.py`, new module) — single endpoint,
  payload varies by `current_user.role`:
  - **Common to all**: `role`, `role_scope` (department name or "All departments")
  - **Agent / dept_manager** (`support_agent`, `dept_manager`): `awaiting_approval_count`
    (Requests with an unresolved decision needing approval, department-scoped via
    `is_department_scoped` same as `app/requests/router.py:65-66`), `sla_breach_soon`
    (top 3 Requests ordered by `sla_first_response_due` ascending, department-scoped),
    `decision_mix` (last-24h `Decision.type` counts — reuse the funnel groupby from
    `app/analytics/router.py:63-66` with `days=1`)
  - **knowledge_manager**: `open_gap_count`, `top_gap` (highest `occurrence_count` from
    the existing knowledge-gaps query used by `listKnowledgeGaps`), `articles_expiring_30d`
    (count of `KnowledgeArticle` with `effective_to` in next 30 days — check
    `app/models/knowledge.py` for the actual field name before wiring this)
  - **executive**: the 5 BO KPIs verbatim from `AnalyticsKpis` (call the same function
    `get_kpis` logic, `days=30`) — no separate computation, just reuse
  - **auditor**: `decision_volume_24h` (count), `override_count_24h` (`rule.applied`
    `AuditEvent` rows in last 24h), `unresolved_exceptions` (best-effort proxy: count of
    Requests with status escalated/held and no closing decision — document as a proxy
    like BO-002 already is)
  - System health tile (LLM provider latency, pgvector chunk count, email queue depth,
    workflow worker count) shown to all roles — **mark as static/mocked in the response**
    if no real health-check plumbing exists yet (check `app/core/` for any existing
    provider-latency tracking before deciding; if none, return nulls/placeholders rather
    than fabricating numbers, and say so in the Delivered notes)
- Permission: reuse `dashboard` module already defined in RBAC matrix
  (`frontend/src/lib/rbac.ts:56`) — mirror it server-side in
  `app/core/permissions.py` if not already present, gate with
  `require_permission("dashboard", Action.READ)`

## Frontend
- `frontend/src/features/dashboard/DashboardPage.tsx` — single component, switches tile
  sets on `role` from the summary response (not on the frontend-only `RoleName` type, to
  avoid drift between client role and server-computed data)
- Reuse existing primitives: `StatusBadge`, KPI tile markup already established in
  `AnalyticsPage.tsx:20-31` (extract shared `KpiTile` if reused as-is, otherwise duplicate
  minimally — don't over-abstract for a 2-user reuse)
- `router.tsx`: add `'/': () => <PermissionGate module="dashboard"><DashboardPage /></PermissionGate>`
  to `REAL_PAGES`, delete the `COMING_IN` entry for `/` (whole map can likely go if `/` was
  its only entry — check before deleting)

## Verification target
- Chrome-verify all 5 seeded role logins (`arip-dev-password`) each see their own tile set
  at `/`, not the placeholder
- `customer` role has no sidebar/dashboard access (portal is separate route tree already)
- No console errors; empty-state per tile type when a role's data is genuinely empty
  (e.g., knowledge_manager with 0 open gaps)

## Delivered
- Backend: `app/dashboard/router.py` (new module), `GET /v1/dashboard/summary`, gated by
  `require_permission("dashboard", Action.READ)` (already in the RBAC matrix, no changes
  needed there). `app/analytics/router.py`'s KPI computation was split into a plain
  `compute_kpis(db, days)` function so the executive tile calls the same code the
  Analytics page uses — no duplicated logic.
  - Agent/dept_manager tiles: `awaiting_approval_count` (department-scoped via the same
    `is_department_scoped` helper `app/requests/router.py` uses), top-3 `sla_breach_soon`
    by `sla_first_response_due` ascending, 24h `decision_mix_24h` by `Decision.type`.
  - knowledge_manager tiles: `open_gap_count` + `top_gap_*` from the real `KnowledgeGap`
    table (same one `GET /v1/gaps` reads), `articles_expiring_30d` from
    `KnowledgeVersion.expires_on`.
  - executive tile: the 5 BO KPIs verbatim, via `compute_kpis`.
  - auditor tiles: `decision_volume_24h`, `override_count_24h` (`Decision.rule_overridden`
    — no `rule.applied` audit-event type actually exists in the codebase, that was a
    design-doc mock string, so this uses the real boolean column instead),
    `unresolved_exceptions` (proxy: Requests in HELD/ROUTED/AWAITING_APPROVAL — the data
    model has no dedicated "exception" concept, same proxy pattern as BO-002).
  - System health tile: **not implemented** — no provider-latency, pgvector-count, or
    queue-depth plumbing exists anywhere in `app/core/`, confirmed by search before
    writing this. Every field in `SystemHealthTile` is null; the frontend shows "No live
    health-check data wired up yet." rather than fabricated numbers.
  - Roles not in the original 5-variant list (`admin`, `super_admin`) get every tile
    (union of all role branches, org-wide/unscoped) since they hold "F" on `dashboard` —
    not in the original spec table but a natural extension of it.
  - 5 new pytest tests in `tests/test_dashboard.py` (one per role branch + a customer
    403), full suite 94/94 passing.
- Frontend: `frontend/src/features/dashboard/{types,api,DashboardPage}.tsx`. Wired into
  `router.tsx`'s `REAL_PAGES['/']`; the now-dead `COMING_IN` map was deleted entirely
  (its only entry was `/`).
- **Verified live in Chrome**: restarted the dev backend (it was running stale code on
  :8010) and logged in as all 5 non-admin seeded roles. Priya (support_agent) saw 0
  awaiting-approval + 2 real SLA-risk rows + a 2-slice decision mix; Daniel (dept_manager)
  saw 1 awaiting-approval + 3 SLA rows scoped to Cards & Payments; Mei (knowledge_manager)
  saw 4 open gaps, top gap "employment verification" at 34 occurrences, 0 expiring;
  Alice (executive) saw all 5 BO tiles with real computed values and targets; Ken
  (auditor) saw 21 decisions / 3 overrides / 11 unresolved exceptions in the last 24h.
  All values matched a direct `curl` against the endpoint. No console errors.
