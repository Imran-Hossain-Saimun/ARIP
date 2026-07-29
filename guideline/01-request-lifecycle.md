# Request Lifecycle

Covers: `backend/app/requests/router.py`, `backend/app/decisions/router.py`,
`backend/app/portal/router.py`, `backend/app/realtime/router.py`,
`backend/app/core/idempotency.py`, `backend/app/models/{request,decision}.py`,
`backend/app/core/permissions.py` (department-scoping functions only — full RBAC matrix
is in [06-rbac-and-audit.md](06-rbac-and-audit.md)).

## 1. Data model

**`Channel`** (`backend/app/models/request.py:12-14`): `WEB`, `EMAIL`.

**`RequestStatus`** (`backend/app/models/request.py:17-29`) — the full state machine:
`RECEIVED`, `PROCESSING`, `AWAITING_CUSTOMER`, `AWAITING_APPROVAL`, `ANSWERED`, `HELD`,
`ROUTED`, `IN_PROGRESS`, `RESOLVED`, `REOPENED`.

**`Priority`** (`:32-36`): `LOW`, `MEDIUM`, `HIGH`, `URGENT`.

**`Request`** (`:39-63`, table `requests`): `reference` (unique, e.g. `REQ-8C1F454B`),
`customer_id` FK (RESTRICT), `channel`, `language` (default `"en"`), `intent`, `category`,
`status` (default `RECEIVED`), `priority` (default `MEDIUM`), `department_id` FK (SET
NULL), `assignee_id` FK (SET NULL), `sla_first_response_due`. Relationships: `customer`,
`department`, `assignee`, `messages`, `attachments`, `decisions`.

**`MessageAuthor`** (`:66-70`): `CUSTOMER`, `AGENT`, `AI`, `SYSTEM`.
**`Message`** (`:73-80`): `request_id` FK CASCADE, `author`, `body`.
**`Attachment`** (`:83-93`): `request_id` FK CASCADE, `message_id` FK SET NULL, `filename`,
`content_type`, `storage_key`, `size_bytes`.

**`DecisionType`** (`backend/app/models/decision.py:11-18`): `AUTO_REPLY`, `DRAFT_REPLY`,
`ASK_CLARIFICATION`, `ROUTE`, `HOLD`.

**`Decision`** (`:21-44`): `request_id` FK CASCADE, `type`, `confidence` (Numeric 5,4),
`threshold` (default 0.95 — **always the auto_reply threshold regardless of which band the
decision actually landed in**, `:30-33`), `signals` (JSON), `stages` (JSON list of
`{key, ms, meta}`), `prompt_version_id` (unconstrained UUID — FK lands with a real
`PromptVersion` table later, `:22-23`), `model`, `latency_ms`, `rule_overridden`.

**`Evidence`** (`:47-64`): `decision_id` FK CASCADE, `chunk_id` FK SET NULL,
`retrieval_mode` ("vector"/"vectorless"), `score`, `locator`, `article_ref`,
`version_ref`. Deliberately denormalized (`:48-52`) — evidence is an immutable record of
what was cited at decision time, so the trace still renders correctly even if the cited
article is later edited or archived.

**`RuleEvaluation`** (`:67-78`): `decision_id` FK CASCADE, `rule_code` (unconstrained
string, e.g. `"BR-022"`), `outcome`, `priority`.

## 2. Every way a Request gets created

1. **Portal submit** (customer-facing, no auth) — `POST /v1/portal/requests`
   (`backend/app/portal/router.py:54-71`) calls `run_pipeline(...)` (`:59`), which creates
   the `Request` at `backend/app/ai/pipeline.py:64-66` with `status=PROCESSING` and runs
   the full pipeline synchronously (classify → retrieve → score → rules → decide). This
   is the **only** creation path that automatically produces a `Decision`.
2. **Email sync** — `sync_mailbox()`/`_process_message()` in `backend/app/email/sync.py`
   create a `Request` with `status=RECEIVED`, `channel=EMAIL` directly — **no call to
   `run_pipeline`** anywhere in this path. Full detail in
   [04-email-processing.md](04-email-processing.md).
3. **Direct staff API** — `POST /v1/requests` (`backend/app/requests/router.py:144-165`,
   permission `requests`/`WRITE`) finds-or-creates the `Customer`, creates a `Request`
   with `status=RECEIVED`, adds the initial message, records a `request.created` audit
   event — and also does **not** call `run_pipeline`.

**Implication for QA**: only requests submitted through the customer portal get an
automatic AI decision. Email-sourced and directly-API-created requests sit at `RECEIVED`
with no `Decision` row until something else acts on them (there is currently no such
"something else" implemented — see [04-email-processing.md](04-email-processing.md) §5).

## 3. `requests/router.py` — every endpoint

Prefix `/v1/requests` (`backend/app/requests/router.py:27`).

| Method + path | Line | Purpose | Permission | Department scoping |
|---|---|---|---|---|
| `GET /v1/requests` | `:52-97` | List/filter/paginate | `requests`/READ (`:55`) | Scoped roles (`support_agent`, `dept_manager`) are forcibly filtered to their own `department_id` (`:65-66`), ignoring any `department_id` query param; non-scoped roles can pass one to filter or omit it to see all |
| `GET /v1/requests/{id}` | `:100-108` | Fetch one request | `requests`/READ (`:104`) | `enforce_department_scope` (`:107`) |
| `GET /v1/requests/{id}/decisions` | `:111-120` | List all decisions for a request, newest first | `decision_trace`/READ (`:115`) | `enforce_department_scope` (`:119`) |
| `POST /v1/requests` | `:144-165` | Direct creation (see §2.3) | `requests`/WRITE (`:148`) | none (no department yet) |
| `PATCH /v1/requests/{id}/assign` | `:168-191` | Reassign department and/or assignee | `reassign_escalate`/WRITE (`:173`) | scope-checked against the request's **current** department (`:176`) |
| `POST /v1/requests/{id}/approve` | `:194-210` | Approve | `approve_send`/APPROVE (`:199`) | `enforce_department_scope` (`:202`) — also requires `Idempotency-Key` |
| `POST /v1/requests/{id}/escalate` | `:213-230` | Escalate with a reason | `reassign_escalate`/WRITE (`:219`) | `enforce_department_scope` (`:222`) — also requires `Idempotency-Key` |

`_load_request_or_404` (`:123-141`) eagerly loads customer/messages/attachments/decisions
(with evidence and rule_evaluations) in one query.

## 4. `decisions/router.py` — every endpoint

Prefix `/v1/decisions` (`backend/app/decisions/router.py:14`).

| Method + path | Line | Purpose | Permission |
|---|---|---|---|
| `GET /v1/decisions/{id}/trace` | `:32-59` | Full explainability trace | `decision_trace`/READ (`:36`) + dept scope (`:39`) |
| `POST /v1/decisions/{id}/replay` | `:62-73` | **Stub** — see below | `decision_trace`/READ (`:66`) + dept scope (`:72`) |

`/trace` response shape (`backend/app/schemas/decisions.py:25-39`, populated at
`decisions/router.py:43-59`):

```json
{
  "decision_id": "...", "request_id": "REQ-8C1F454B",
  "type": "draft_reply", "confidence": 0.87, "threshold": 0.95,
  "signals": {...}, "stages": [{"key": "intake", "ms": 12, "meta": {}}, ...],
  "evidence": [{"chunk_id": "...", "article": "...", "version": "...", "locator": "§2.1", "mode": "vector", "score": 0.81}],
  "rules": [{"id": "BR-022", "outcome": "require_human", "priority": 10}],
  "model": "claude-sonnet-4.6", "prompt_version": null,
  "audit_hash": "sha256:..."
}
```
`request_id` in the trace is the human-facing reference code, not the UUID.
`prompt_version` is hardcoded `null` — no real `PromptVersion` table exists yet
(`decisions/router.py:57`). `audit_hash` comes from the `AuditEvent` whose
`object_ref == f"decision:{decision_id}"` (`:41,58`).

**`/replay` does not re-run anything.** Docstring: "Stub: the real AI pipeline ... lands
in increment 9. For now this confirms the decision exists and is replay-eligible"
(`:68-70`). It only checks existence + department scope, then returns
`{decision_id, replayed: false, message: "..."}` (`:73`) — `replayed` is always `false`.
**This stub was never revisited after increment 9 landed** — worth flagging if a
developer expects real replay to work.

## 5. Approve / escalate / assign — transitions, audit, idempotency

| Action | Status transition | Audit event | Idempotency-gated |
|---|---|---|---|
| Assign | none | `request.assigned`, payload `{assignee_id, department_id}` (`requests/router.py:183-189`) | no |
| Approve | any → `ANSWERED` (unconditional, `:207`) | `request.approved` (`:208`) | yes |
| Escalate | any → `ROUTED` (`:227`) | `request.escalated`, payload `{reason}` (`:228`) | yes |

Both approve and escalate replay the *current* row unchanged (no re-mutation, no new
audit event) if the same `Idempotency-Key` is reused for the same request (`:204-205`,
`:224-225`, comment: "replayed request — return current state, don't re-apply the
mutation").

**Idempotency implementation** (`backend/app/core/idempotency.py`):
```python
_seen_keys: set[tuple[str, str]] = set()   # :6 — in-process, no persistence, no TTL
```
- `require_idempotency_key(...)` (`:9-15`): FastAPI header dependency, 400s if the
  `Idempotency-Key` header is missing/blank.
- `check_and_record(endpoint, idempotency_key)` (`:18-22`): dedup key is
  `(endpoint, idempotency_key)`. Callers namespace the key value by request id
  (`f"{idempotency_key}:{request_id}"`, `requests/router.py:204,224`) so the same header
  value can't collide across two different requests.
- **No TTL, no Redis** — a key is blocked forever for the life of the process. Comment:
  "swap for a Redis-backed store (shared across replicas, with a TTL) before running more
  than one API instance" (`idempotency.py:3-5`).

## 6. Department scoping (`backend/app/core/permissions.py`)

```python
_DEPARTMENT_SCOPED_ROLES = {RoleName.SUPPORT_AGENT, RoleName.DEPT_MANAGER}   # :85
```
- `is_department_scoped(role)` (`:88-89`) — simple membership check, used by the request
  list endpoint to decide whether to force-filter.
- `enforce_department_scope(user, department_id)` (`:92-106`) — no-op for any role **not**
  in the scoped set (`super_admin`, `admin`, `knowledge_manager`, `executive`, `auditor`,
  `customer` all pass through unrestricted). For a scoped role, raises 403 if
  `department_id is None` **or** doesn't match `user.department_id` — note a request with
  no department at all is treated as forbidden to scoped roles, not permitted.

## 7. Portal endpoints (public, no auth)

Prefix `/v1/portal` (`backend/app/portal/router.py:22`). None of these depend on
`CurrentUser`/`require_permission`.

| Method + path | Line | Purpose |
|---|---|---|
| `POST /v1/portal/requests` | `:54-71` | Public intake; runs `run_pipeline` synchronously; returns reference, status, a UI-friendly `progress_stage`, the AI reply if any, and citations (**only** when decision type is `auto_reply`/`draft_reply`, `:63`) |
| `GET /v1/portal/requests/{reference}?email=...` | `:74-83` | Track by reference + email |
| `POST /v1/portal/requests/{reference}/feedback` | `:86-97` | 1-5 star rating + comment, only once status is `ANSWERED`/`RESOLVED` |

**Anti-enumeration lookup** — `_load_by_reference_and_email` (`:39-51`) filters on
**both** `Request.reference == reference` AND `Customer.email == email` in a single
`WHERE` (`:43`). Wrong reference, wrong email, or both → the exact same 404
(`{"code": "not_found", "message": "No request found for that reference and email."}`,
`:47-50`). Comment: "don't leak which one was correct to an unauthenticated caller"
(`:48-49`). Both `track_request` and `submit_feedback` share this helper.

`_PROGRESS_STAGE` mapping (`:25-36`) collapses 10 internal statuses into 4 customer-facing
labels: `RECEIVED`→"Received", `PROCESSING`→"Reviewed",
`AWAITING_CUSTOMER`/`AWAITING_APPROVAL`/`HELD`/`ROUTED`/`IN_PROGRESS`/`REOPENED`→"Preparing
answer", `ANSWERED`/`RESOLVED`→"Resolved".

## 8. Realtime SSE (`backend/app/realtime/router.py`)

`GET /v1/stream` (`:47-49`) — requires an authenticated user, but **no department/role
filtering**: any authenticated user sees every audit event in the system.

Mechanism (`_event_stream()`, `:23-44`):
1. Yields `event: connected\ndata: {}\n\n` immediately (`:26`).
2. Establishes a watermark from the single most recent `AuditEvent` (`ORDER BY occurred_at
   DESC LIMIT 1`) so the stream never replays history (`:28-30`).
3. Loops up to `_MAX_ITERATIONS = 60` (`:20`) times: queries all events newer than the
   watermark, yields one `event: audit_event` message per row, advances the watermark,
   yields a heartbeat comment, sleeps `_POLL_INTERVAL_SECONDS = 2` (`:19`).
4. After ~2 minutes total, the generator returns and the connection closes — the
   browser's `EventSource` auto-reconnects, which stands in for the spec's "SSE reconnect
   with backoff" without any server-side backoff logic (`:15-18`).

Event payload:
```
event: audit_event
data: {"event_type": "...", "actor": "...", "object_ref": "...", "occurred_at": "..."}
```

## 9. Known limitations (from code comments, this module)

- **`/replay` is a stub** — no real pipeline re-run (`decisions/router.py:68-70`).
- **`prompt_version` always null** — `PromptVersion` FK not yet wired
  (`decisions/router.py:57`, `models/decision.py:22-23`).
- **`RuleEvaluation.rule_code` unconstrained** — no `BusinessRule` FK
  (`models/decision.py:68`).
- **Idempotency store is in-process, no TTL** — single API instance only
  (`core/idempotency.py:3-5`).
- **SSE is polling, not push**, capped at ~2 minutes per connection
  (`realtime/router.py:15-18`).
- **Direct `POST /v1/requests` bypasses the AI pipeline entirely** — creates a bare
  `RECEIVED` request with no `Decision` (observed behavior, not code-commented — worth QA
  attention alongside the email-sync gap in
  [04-email-processing.md](04-email-processing.md)).
