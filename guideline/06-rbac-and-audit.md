# RBAC & Audit Trail

Covers: `backend/app/core/permissions.py`, `backend/app/core/audit.py`,
`backend/app/models/{audit,user}.py`, `backend/app/audit/router.py`.

## 1. The permission matrix, as data

`Action` enum (`backend/app/core/permissions.py:25-29`): `READ`, `WRITE`, `APPROVE`,
`DELETE`.

Access-level letters map to action sets (`_LEVEL_ACTIONS`, `:32-38`):

| Code | Meaning | Actions granted |
|---|---|---|
| `F` | full | READ, WRITE, APPROVE, DELETE |
| `W` | write (own department) | READ, WRITE — department scoping enforced by the *caller*, not this map (`:5-6`) |
| `R` | read | READ |
| `A` | approve only | READ, APPROVE |
| `-` | none | (empty) |

`RoleName` (`backend/app/models/user.py:11-21`): `SUPER_ADMIN`, `ADMIN`,
`KNOWLEDGE_MANAGER`, `DEPT_MANAGER`, `SUPPORT_AGENT`, `EXECUTIVE`, `AUDITOR`, `CUSTOMER`.

`_ROLE_ORDER` (`permissions.py:43-52`) fixes the column order for `_MATRIX`
(`:54-71`), one row per module, one letter per role in that order:

| Module | SUPER_ADMIN | ADMIN | KNOWLEDGE_MGR | DEPT_MGR | SUPPORT_AGENT | EXECUTIVE | AUDITOR | CUSTOMER |
|---|---|---|---|---|---|---|---|---|
| `dashboard` | F | F | F | F | F | R | R | - |
| `requests` | F | F | R | W | W | - | R | R |
| `approve_send` | F | F | - | A | A | - | - | - |
| `reassign_escalate` | F | F | - | F | W | - | - | - |
| `decision_trace` | F | F | R | R | R | - | R | - |
| `email` | F | F | - | W | W | - | R | - |
| `knowledge_authoring` | F | F | F | W | R | - | R | - |
| `knowledge_approval` | F | A | A | A | - | - | R | - |
| `workflow_builder` | F | F | - | R | - | - | R | - |
| `routing_config` | F | F | - | W | - | - | R | - |
| `business_rules` | F | F | - | - | - | - | R | - |
| `prompt_management` | F | F | W | - | - | - | R | - |
| `analytics` | F | F | R | R | - | F | R | - |
| `audit_logs` | F | R | R | - | - | - | F | - |
| `admin_users` | F | F | - | R | - | - | R | - |
| `integrations` | F | W | - | - | - | - | R | - |

`PERMISSIONS` (`:73-76`) zips `_ROLE_ORDER` against each split row through
`_LEVEL_ACTIONS`, building `dict[Module, dict[RoleName, frozenset[Action]]]`.
`has_permission(role, module, action)` (`:79-80`) is a plain frozenset membership check.

## 2. Department scoping — layered on top of the matrix

```python
_DEPARTMENT_SCOPED_ROLES = {RoleName.SUPPORT_AGENT, RoleName.DEPT_MANAGER}   # :85
```
- `is_department_scoped(role)` (`:88-89`) — membership check.
- `enforce_department_scope(user, department_id)` (`:92-106`) — no-op for any role not in
  the scoped set. For a scoped role, 403s if `department_id is None` **or** doesn't match
  `user.department_id`. Full usage detail in
  [01-request-lifecycle.md](01-request-lifecycle.md) §6.

## 3. `assert_permission()` / `require_permission()`

**`assert_permission(user, module, action, db=None)`** (`:109-135`):
- Checks `has_permission(user.role, module, action)` (`:117`).
- **On denial, if `db` is provided**: writes an `access.denied` audit event
  (`event_type="access.denied"`, `actor=user.email`, `object_ref=module`,
  `payload={"role": ..., "action": ...}`, `:119-125`), commits it (`:126`), **then** raises
  `HTTPException(403, ...)` (`:127-134`) — so the denial itself is durably recorded even
  though the triggering request fails. Docstring: "a denial is itself an auditable event,
  not just a silent 403" (`:114-116`). `db` should only be omitted for in-memory checks
  with no session in scope (e.g. plain unit tests of the matrix itself).

**`require_permission(module, action)`** (`:138-143`) — the common-case FastAPI
dependency wrapper:
```python
def require_permission(module, action):
    def dependency(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
        assert_permission(current_user, module, action, db)
        return current_user
    return Depends(dependency)
```
Used directly as a route default, e.g. `_user=require_permission("audit_logs",
Action.READ)` — every gated endpoint in the app follows this exact pattern (see the
per-module docs for the specific module/action pairs each endpoint requires).

## 4. The audit hash chain (`backend/app/core/audit.py`)

**`AuditEvent`** model (`backend/app/models/audit.py:10-22`) — "append-only, sha256
hash-chained. Never updated or deleted." Fields: `event_type` (indexed), `actor` (email,
`String(320)`), `object_ref` (indexed), `payload` (JSON), `prev_hash` (`String(71)`,
nullable — `None` for the first event ever), `hash` (`String(71)`, **unique**),
`occurred_at`.

**`record_audit_event(db, *, event_type, actor, object_ref, payload=None)`**
(`audit.py:21-40`) — "the only sanctioned way to write an audit row... every mutation
writes an audit event in the same transaction" (`:22-24`):
1. `SELECT ... ORDER BY occurred_at DESC LIMIT 1 FOR UPDATE` (`:26`) — locks the latest
   row so two concurrent writers can't both read the same "last" row and independently
   compute the same `prev_hash`, which would fork the chain.
2. `prev_hash = last.hash if last else None`.
3. Builds the new row with `hash = _compute_hash(prev_hash, event_type, actor,
   object_ref, payload)`.
4. `db.add()` + `db.flush()` — **no commit**; the caller's transaction commits it.

**`_compute_hash(prev_hash, event_type, actor, object_ref, payload)`** (`:12-18`):
```python
digest_input = json.dumps(
    {"prev_hash": prev_hash, "event_type": event_type, "actor": actor,
     "object_ref": object_ref, "payload": payload},
    sort_keys=True, default=str,
).encode("utf-8")
return f"sha256:{hashlib.sha256(digest_input).hexdigest()}"
```
Note: `occurred_at` and the row's own `id` are **not** part of the hash input — only
those 5 fields.

**`verify_chain(db)`** (`:43-54`) — "walks every event in insertion order and recomputes
each hash." Loads all events ordered by `occurred_at` ascending, walks with a running
`prev_hash` starting at `None`:
```python
expected = _compute_hash(prev_hash, event.event_type, event.actor, event.object_ref, event.payload)
if event.prev_hash != prev_hash or event.hash != expected:
    return False, len(events), event.id   # first broken link
prev_hash = event.hash
```
Returns `(True, len(events), None)` if the whole chain verifies. The break condition
covers both a tampered row's own fields (`hash != expected`) and a discontinuity/fork in
the chain (`prev_hash != prev_hash`).

## 5. Every endpoint (`backend/app/audit/router.py`)

Prefix `/v1/audit` (`:14`).

| Method + path | Line | Purpose | Permission |
|---|---|---|---|
| `GET /v1/audit` | `:17-39` | Paginated/filterable list (`type`, `actor`, `object`, `from`/`to`), `limit` capped at 500 | `audit_logs`/READ |
| `GET /v1/audit/verify` | `:42-46` | Runs `verify_chain(db)`, returns `{valid, event_count, broken_at_id}` | `audit_logs`/READ |
| `GET /v1/audit/export` | `:49-53` | Full, unpaginated export, ordered ascending | `audit_logs`/READ |

Per the matrix, `audit_logs` is `F` for `super_admin`/`auditor`, `R` for `admin`/
`knowledge_manager`, `-` for everyone else — so any role with at least read access can
hit all three endpoints including export and verify (all three only require READ).

## 6. Known limitations (from code comments)

- `record_audit_event` is declared "the only sanctioned way to write an audit row" —
  anything that inserts `AuditEvent` directly elsewhere would break the intended
  invariant (hash-chain integrity, atomicity with the triggering mutation).
- `AuditEvent` rows are documented append-only, but that's enforced by usage discipline —
  there is no DB-level trigger/constraint visible in this codebase preventing an update or
  delete.
- `export_audit_events` is explicitly a scalability simplification: "small enough for this
  build's data volume; a real deployment would stream this rather than load it all into
  memory" (`audit/router.py:51-52`).
- The `with_for_update()` lock in `record_audit_event` is explicitly there to prevent
  concurrent writers from forking the chain — an implicit acknowledgment that without it,
  chain integrity would be at risk under concurrency.
- As noted in [05-automation-versioned-config.md](05-automation-versioned-config.md),
  the automation subsystem's publish/rollback actions do **not** write audit events —
  only the RBAC-denial path and the request/decision/email flows documented elsewhere do.
