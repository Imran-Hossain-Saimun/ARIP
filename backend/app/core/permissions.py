"""§12 RBAC matrix, encoded as data (not enforced by any UI-only gate).

Access levels from the spec:
  F  full            -> read, write, approve, delete
  W  write (own dept) -> read, write            (department scoping is enforced by the
                                                   caller filtering on department_id, not here)
  R  read             -> read
  A  approve only      -> read, approve
  -  no access         -> nothing
"""

import enum
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.db import get_db
from app.core.security import CurrentUser
from app.models.user import RoleName, User


class Action(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    APPROVE = "approve"
    DELETE = "delete"


_LEVEL_ACTIONS: dict[str, frozenset[Action]] = {
    "F": frozenset({Action.READ, Action.WRITE, Action.APPROVE, Action.DELETE}),
    "W": frozenset({Action.READ, Action.WRITE}),
    "R": frozenset({Action.READ}),
    "A": frozenset({Action.READ, Action.APPROVE}),
    "-": frozenset(),
}

Module = str

# Row = module, columns = roles, in the exact order the spec's table gives them.
_ROLE_ORDER = [
    RoleName.SUPER_ADMIN,
    RoleName.ADMIN,
    RoleName.KNOWLEDGE_MANAGER,
    RoleName.DEPT_MANAGER,
    RoleName.SUPPORT_AGENT,
    RoleName.EXECUTIVE,
    RoleName.AUDITOR,
    RoleName.CUSTOMER,
]

_MATRIX: dict[Module, str] = {
    "dashboard": "F F F F F R R -",
    "requests": "F F R W W - R R",
    "approve_send": "F F - A A - - -",
    "reassign_escalate": "F F - F W - - -",
    "decision_trace": "F F R R R - R -",
    "email": "F F - W W - R -",
    "knowledge_authoring": "F F F W R - R -",
    "knowledge_approval": "F A A A - - R -",
    "workflow_builder": "F F - R - - R -",
    "routing_config": "F F - W - - R -",
    "business_rules": "F F - - - - R -",
    "prompt_management": "F F W - - - R -",
    "analytics": "F F R R - F R -",
    "audit_logs": "F R R - - - F -",
    "admin_users": "F F - R - - R -",
    "integrations": "F W - - - - R -",
}

PERMISSIONS: dict[Module, dict[RoleName, frozenset[Action]]] = {
    module: {role: _LEVEL_ACTIONS[level] for role, level in zip(_ROLE_ORDER, levels.split())}
    for module, levels in _MATRIX.items()
}


def has_permission(role: RoleName, module: Module, action: Action) -> bool:
    return action in PERMISSIONS.get(module, {}).get(role, frozenset())


# FR-063 department isolation: these roles' "W"/"A" access is scoped to their own
# department row-by-row, not just gated at the module level.
_DEPARTMENT_SCOPED_ROLES = {RoleName.SUPPORT_AGENT, RoleName.DEPT_MANAGER}


def is_department_scoped(role: RoleName) -> bool:
    return role in _DEPARTMENT_SCOPED_ROLES


def enforce_department_scope(user: User, department_id: uuid.UUID | None) -> None:
    """Raise 403 if a department-scoped role tries to touch a row outside their own
    department. Full/global roles (super_admin, admin, executive, auditor) pass through."""
    if user.role not in _DEPARTMENT_SCOPED_ROLES:
        return
    if department_id is None or department_id != user.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "forbidden",
                "message": "This request belongs to a different department.",
                "field_errors": [],
                "trace_id": None,
            },
        )


def assert_permission(user: User, module: Module, action: Action, db: Session | None = None) -> None:
    """Non-Depends variant for routes where `module` is only known at request time (e.g.
    a `{kind}` path param covering several §12 modules) — `require_permission` below
    covers the common case where `module` is static and known at route-decoration time.

    §13 non-negotiable / increment-8 E2E target: a denial is itself an auditable event,
    not just a silent 403 — pass `db` to record it (omit only for the rare in-memory
    check that has no session in scope, e.g. plain unit tests of the matrix itself)."""
    if not has_permission(user.role, module, action):
        if db is not None:
            record_audit_event(
                db,
                event_type="access.denied",
                actor=user.email,
                object_ref=module,
                payload={"role": user.role.value, "action": action.value},
            )
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "forbidden",
                "message": f"Role '{user.role.value}' cannot '{action.value}' on '{module}'.",
                "field_errors": [],
                "trace_id": None,
            },
        )


def require_permission(module: Module, action: Action):
    def dependency(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
        assert_permission(current_user, module, action, db)
        return current_user

    return Depends(dependency)
