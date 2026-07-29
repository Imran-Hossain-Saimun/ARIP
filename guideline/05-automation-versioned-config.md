# Automation: Versioned Config (Workflows / Routing / Business Rules / Prompts)

Covers: `backend/app/core/versioned_config.py`, `backend/app/automation/router.py`,
`backend/app/models/automation.py`.

Four conceptually different automation surfaces from the spec — workflows, routing
rules, business rules, prompt templates — share **one table and one lifecycle
implementation**. This is the single highest-leverage design decision in the codebase
(see `tasks/07-automation.md`).

## 1. Data model

**`ConfigResourceKind`** (`backend/app/models/automation.py:12-19`): `WORKFLOW`,
`BUSINESS_RULE`, `PROMPT_TEMPLATE`, `ROUTING_RULE`.

**`ConfigResourceStatus`** (`:22-25`): `DRAFT`, `ACTIVE`, `ARCHIVED`.

**`ConfigResource`** (`:28-48`): `kind`, `key` (logical id, e.g. `"BR-022"` or
`"reply_draft_prompt"`), `name`, `version` (int, default 1), `status` (default `DRAFT`),
`config` (JSON — kind-specific payload: rule when/then, prompt text, workflow graph,
routing entry), `description`, `created_by` FK (SET NULL), `activated_at`. **Design
invariant** (`:31-33`): every edit is a **new row** with an incremented `version` under
the same `(kind, key)` — never an in-place update. Publish/rollback just flip which
version is `ACTIVE`.

**`WorkflowRunStatus`** (`:51-54`): `RUNNING`, `SUCCEEDED`, `FAILED`.
**`WorkflowRun`** (`:57-70`): `workflow_key`, `request_id` FK (SET NULL), `status`
(default `RUNNING`), `started_at`/`finished_at`, has many `actions`.

**`WorkflowActionStatus`** (`:73-76`): `SUCCEEDED`, `FAILED`, `RETRIED`.
**`WorkflowAction`** (`:79-89`): `run_id` FK CASCADE, `action_type`, `status`,
`error_message`, `executed_at`.

## 2. The draft → active → archived lifecycle (`backend/app/core/versioned_config.py`)

- **`list_current(db, kind)`** (`:24-34`) — one row per `key`: the `ACTIVE` version if one
  exists, else the newest `DRAFT`.
- **`list_versions(db, kind, key)`** (`:37-39`) — full version history, newest first.
- **`create_draft(db, *, kind, key, name, config, description, user)`** (`:42-47`) —
  computes `max_version` for `(kind, key)`, inserts a new row at `max_version + 1` with
  `status=DRAFT`. `db.flush()` only — commit is the router's responsibility.
- **`publish(db, resource)`** (`:50-66`) — "activate this version; archive whatever was
  previously active under the same `(kind, key)` — never more than one `ACTIVE` row per
  key" (`:51-52`). Queries all currently-`ACTIVE` rows for the same `(kind, key)`, sets
  each to `ARCHIVED`, then sets the target to `ACTIVE` and stamps `activated_at`.
- **`rollback(db, *, kind, key, target_version)`** (`:69-78`) — looks up the historical
  row by exact version number, 404s if not found, then **literally calls `publish()`** on
  that old row (`:78`) — rollback reuses the exact same archive-then-activate logic;
  reactivating an old version is itself just another "activation event," not a distinct
  code path.

**No audit events are written by any of these three functions.** Confirmed by grep — no
`AuditEvent`/`record_audit_event` reference anywhere in `versioned_config.py` or
`automation/router.py`. The only audit event connected to this subsystem at all is the
permission layer's `access.denied` event on a failed authorization check (see
[06-rbac-and-audit.md](06-rbac-and-audit.md)) — successful draft/publish/rollback actions
are **not** audited, unlike request approve/escalate.

## 3. `simulate_business_rule` — read-only dry-run

`versioned_config.py:86-102`. Signature: `simulate_business_rule(db, when: dict, days:
int = 30) -> dict`.

- Queries `Decision` joined to `Request` where `Decision.created_at >= now - days`.
- For each key in `when`: `confidence_gte` filters `Decision.confidence >= value`; any
  key in the allowlist `_MATCHABLE_FIELDS = {"category", "intent", "channel", "priority"}`
  (`:83`) filters the matching `Request` field via `getattr`. Keys outside this allowlist
  are silently ignored. Comment: allowlist is "kept... rather than arbitrary attribute
  access" — a deliberate safety choice (`:81-82`).
- Returns `{"window_days": days, "matched": <count>, "would_change_outcome": <count where
  rule_overridden is False>}`.
- **Confirmed pure read-only** — only builds a `select()` and calls `db.execute(...).all()`;
  no `db.add`/`flush`/`commit` anywhere in the function.

## 4. Connection to the AI pipeline

`backend/app/ai/pipeline.py:18` imports `ConfigResource, ConfigResourceKind,
ConfigResourceStatus` from the exact same module, and at `pipeline.py:88-90` queries the
identical `(kind=BUSINESS_RULE, status=ACTIVE)` filter that `list_current`/`publish` use
here. **Business rules authored and published through this subsystem's lifecycle are
exactly the rows the live pipeline reads at inference time** — same table, same `kind`,
same `ACTIVE` filter. See
[03-ai-pipeline-and-llm-providers.md](03-ai-pipeline-and-llm-providers.md) §3 for the
matching logic itself.

## 5. Every endpoint (`backend/app/automation/router.py`)

Prefix `/v1` (`:30`). `KIND_MODULE` (`:34-39`) maps each kind to its RBAC module:
`WORKFLOW→workflow_builder`, `BUSINESS_RULE→business_rules`,
`PROMPT_TEMPLATE→prompt_management`, `ROUTING_RULE→routing_config`.

**Generic surface** — one implementation, all four kinds:

| Method + path | Line | Purpose | Permission |
|---|---|---|---|
| `GET /v1/automation/{kind}` | `:44-47` | `list_current` for a kind | `KIND_MODULE[kind]`/READ |
| `GET /v1/automation/{kind}/{key}/versions` | `:50-53` | `list_versions` | `KIND_MODULE[kind]`/READ |
| `POST /v1/automation/{kind}` | `:56-62` | `create_draft` | `KIND_MODULE[kind]`/WRITE |
| `POST /v1/automation/{resource_id}/publish` | `:65-72` | `publish` (kind inferred from the fetched resource) | `KIND_MODULE[resource.kind]`/APPROVE |
| `POST /v1/automation/{kind}/{key}/rollback/{version}` | `:75-81` | `rollback` | `KIND_MODULE[kind]`/APPROVE |

**Spec-literal aliases** — thin wrappers over the same functions, matching the design
doc's exact endpoint names:

| Method + path | Line | Purpose | Permission |
|---|---|---|---|
| `GET /v1/workflows` | `:86-88` | list current workflows | `workflow_builder`/READ |
| `GET /v1/workflows/runs` | `:91-94` | list `WorkflowRun` history w/ actions | `workflow_builder`/READ |
| `POST /v1/workflows/{id}/publish` | `:97-105` | publish, 404s if not kind `WORKFLOW` | `workflow_builder`/APPROVE |
| `POST /v1/workflows/runs/{run_id}/actions/{action_id}/retry` | `:108-124` | flips a `WorkflowAction` to `RETRIED`, clears error, stamps `executed_at` | `workflow_builder`/WRITE |
| `GET /v1/rules` | `:127-129` | list current business rules | `business_rules`/READ |
| `POST /v1/rules/simulate` | `:132-134` | `simulate_business_rule` dry-run | `business_rules`/READ |
| `GET /v1/prompts` | `:137-139` | list current prompts | `prompt_management`/READ |
| `GET /v1/prompts/{id}/versions` | `:142-145` | resolve id→key, list all versions | `prompt_management`/READ |
| `POST /v1/prompts/{id}/rollback` | `:148-158` | rollback by resource id (not version number); 404s if not kind `PROMPT_TEMPLATE` | `prompt_management`/APPROVE |
| `GET /v1/routing` | `:161-163` | list current routing rules | `routing_config`/READ |

## 6. Known limitations (from code comments)

- **No live workflow execution engine.** `WorkflowRun` docstring: "Runs are seeded/
  recorded here but there is no live execution engine in this build... a real engine
  would create these rows as workflows actually fire on decisions" (`automation.py:58-60`).
  `retry_workflow_action` doesn't re-execute anything — it's bookkeeping only.
- **Rule WHEN-clause matching is a small explicit allowlist**, not arbitrary attribute
  access, deliberately for safety (`versioned_config.py:81-83`).
- **No audit trail for lifecycle transitions** — create_draft/publish/rollback write no
  audit event, unlike request approve/escalate. Worth flagging as an asymmetry.
- **`list_current`'s "current" is a fallback semantic**: a key with no published version
  yet still shows its newest draft in generic listing endpoints
  (`versioned_config.py:25`).
