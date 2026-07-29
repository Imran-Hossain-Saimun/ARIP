# Increment 7 — Automation: workflow builder, routing, business rules, prompts

**Status:** done — verified live in Chrome

## Scope
All four are versioned-config CRUD with diff, simulate, approve, rollback — build ONE
abstraction, reuse four times. This is the single highest-leverage increment for
avoiding duplicated code.

## Backend
- Models: `WorkflowDefinition`, `WorkflowRun`, `WorkflowAction`, `ApprovalTask`,
  `BusinessRule`, `RuleEvaluation` (add FK back onto existing unconstrained `rule_code`
  string column), `PromptTemplate`, `PromptVersion` (add FK back onto
  `Decision.prompt_version_id`, currently unconstrained)
- Shared versioned-config pattern: every one of these four resources gets create-draft →
  diff-against-active → simulate (dry-run against last 30 days of traffic) → approve →
  activate → rollback. Build this as one reusable service/router factory, not four
  copies.
- `GET /v1/workflows`, `GET /v1/workflows/runs`, `POST /v1/workflows/:id/publish`,
  `POST /v1/workflows/runs/:id/actions/:aid/retry`
- `GET /v1/rules`, `POST /v1/rules/simulate`
- `GET /v1/prompts/:id/versions`, `POST /v1/prompts/:id/rollback`
- Department routing: intent→department matrix, escalation matrix, load balancing

## Frontend
- `WorkflowBuilder`: CanvasToolbar, `WorkflowCanvas` (nodes/edges, arrow-key navigable
  per §04 a11y), `NodeInspector`
- Routing rules screen, intent→department matrix, escalation matrix, dept load bars
- Business rules: rule registry (WHEN/THEN expressions), confidence threshold matrix by
  category, conflict detector, what-if simulator
- Prompt management: template list, editor w/ diff, version history, rollback, win-rate/
  citation-compliance/injection-blocked metrics

## Verification target
- A rule change simulated against historical traffic before it can be published
- Rollback restores the exact prior version (diffable)

## Delivered
- Backend: **one generic table, `ConfigResource`** (kind ∈ {workflow, business_rule,
  prompt_template, routing_rule}, key, name, version, status ∈ {draft, active, archived},
  config JSON, description) plus `WorkflowRun`/`WorkflowAction` for execution history
  (migration `f4e073907d71`). `app/core/versioned_config.py` is the single shared
  implementation of the lifecycle: `create_draft` (auto-increments version per key),
  `publish` (activates this version, archives whatever was previously active under the
  same key — never more than one ACTIVE row per key), `rollback` (reactivates an older
  version by version number), `simulate_business_rule` (real query — dry-runs a WHEN
  clause against the last N days of actual Decision+Request rows, no rows written,
  matches on category/intent/channel/priority/confidence_gte). `app/automation/router.py`
  exposes both a generic surface (`/v1/automation/{kind}`, .../{kind}/{key}/versions,
  .../{id}/publish, .../{kind}/{key}/rollback/{version}) AND the spec-literal aliases
  (`/v1/workflows`, `/v1/workflows/runs`, `/v1/rules`, `/v1/rules/simulate`, `/v1/prompts`,
  `/v1/prompts/:id/versions`, `/v1/prompts/:id/rollback`, `/v1/routing`) as thin wrappers
  — satisfies both genuine code reuse and the documented API shape. RBAC: each
  `ConfigResourceKind` maps to its own §12 module (workflow→workflow_builder,
  business_rule→business_rules, prompt_template→prompt_management,
  routing_rule→routing_config) via `assert_permission` (a new non-Depends variant of
  `require_permission` for routes where the module is only known at request time). 9 new
  pytest tests (63 total).
- Seed script: BR-022/BR-014 (matching the rule_hold codes already used by increment 3's
  request seed data), a `reply_draft_prompt`, a `dispute_charge_routing` rule, and a
  `card_dispute_escalation` workflow — all created as v1 and immediately published. Plus
  2 seeded `WorkflowRun`s (one succeeded with 2 actions, one failed with a retryable
  action) for the runs panel to have something real to show.
- Frontend: **one generic component, `ConfigResourceListPage`**, parametrized by
  kind/module/title/config-placeholder and instantiated 4 times
  (`WorkflowsPage`/`BusinessRulesPage`/`PromptsPage`/`RoutingPage`) — mirrors the
  backend's single-table design exactly. Shared `ConfigResourceDrawer` (version history +
  publish/rollback buttons, gated by the `approve` action per module) and
  `CreateDraftForm` (Modal-based). `RuleSimulatorPanel` (business_rule only) and
  `WorkflowRunsPanel` (workflow only, with a working Retry button) are passed in via the
  list page's `extra` slot rather than being bespoke pages.
- **Verified live in Chrome** (after finding and documenting a viewport-coordinate
  drift issue in the browser tool — see `[[claude-in-chrome-flakiness]]`): logged in as
  Admin, Business Rules page shows both seeded rules as active, the what-if simulator
  correctly reported "1 decisions match, of which 0 would change outcome" for `{"category":
  "Legal"}` (Mei Tanaka's request — already held, so correctly 0 "would change"), the
  rule drawer showed the formatted WHEN/THEN config and version history, Workflows page
  showed both seeded runs with the failed action's error message and a working Retry
  button (clicking it correctly cleared the error/retry UI for that action), and Prompts
  page listed the seeded prompt. No console errors.
- **Simplifications, clearly scoped down from the plan**:
  - Config is edited as raw JSON in one generic form — no bespoke `RuleBuilder`,
    `WorkflowCanvas`, `PromptEditor`+diff, or routing-matrix grid UI. The real lifecycle
    (draft → simulate → publish → rollback) works regardless of how the config was typed.
  - No live workflow **execution** engine — `WorkflowRun`/`WorkflowAction` rows are
    seeded/recorded, not produced by an actual engine reacting to decisions. Retry marks
    an action `retried`; it doesn't re-attempt the underlying webhook/task.
  - `simulate_business_rule` matches on a small explicit field allowlist (category,
    intent, channel, priority, confidence_gte) — not a general rule-expression evaluator.
  - Department routing (intent→department matrix, escalation matrix, load balancing) is
    represented as generic `ConfigResource` rows, not a dedicated matrix/load-bar UI.
