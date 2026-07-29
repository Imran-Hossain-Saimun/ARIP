import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.permissions import Action, assert_permission, require_permission
from app.core.security import CurrentUser
from app.core.versioned_config import (
    create_draft,
    get_resource_or_404,
    list_current,
    list_versions,
    publish,
    rollback,
    simulate_business_rule,
)
from app.models.automation import ConfigResourceKind, WorkflowAction, WorkflowActionStatus, WorkflowRun
from app.schemas.automation import (
    ConfigResourceCreate,
    ConfigResourceOut,
    SimulateBody,
    SimulateResult,
    WorkflowRunOut,
)

router = APIRouter(prefix="/v1", tags=["automation"])

# §12 module each ConfigResourceKind is gated by — used for the generic /automation/{kind}
# routes where the kind (and therefore the module) is only known at request time.
KIND_MODULE = {
    ConfigResourceKind.WORKFLOW: "workflow_builder",
    ConfigResourceKind.BUSINESS_RULE: "business_rules",
    ConfigResourceKind.PROMPT_TEMPLATE: "prompt_management",
    ConfigResourceKind.ROUTING_RULE: "routing_config",
}


# ---- Generic surface: one implementation, all four kinds ----------------------------

@router.get("/automation/{kind}", response_model=list[ConfigResourceOut])
def generic_list(kind: ConfigResourceKind, db: Annotated[Session, Depends(get_db)], current_user: CurrentUser):
    assert_permission(current_user, KIND_MODULE[kind], Action.READ, db)
    return list_current(db, kind)


@router.get("/automation/{kind}/{key}/versions", response_model=list[ConfigResourceOut])
def generic_versions(kind: ConfigResourceKind, key: str, db: Annotated[Session, Depends(get_db)], current_user: CurrentUser):
    assert_permission(current_user, KIND_MODULE[kind], Action.READ, db)
    return list_versions(db, kind, key)


@router.post("/automation/{kind}", response_model=ConfigResourceOut, status_code=status.HTTP_201_CREATED)
def generic_create_draft(kind: ConfigResourceKind, body: ConfigResourceCreate, db: Annotated[Session, Depends(get_db)], current_user: CurrentUser):
    assert_permission(current_user, KIND_MODULE[kind], Action.WRITE, db)
    resource = create_draft(db, kind=kind, key=body.key, name=body.name, config=body.config, description=body.description, user=current_user)
    db.commit()
    db.refresh(resource)
    return resource


@router.post("/automation/{resource_id}/publish", response_model=ConfigResourceOut)
def generic_publish(resource_id: uuid.UUID, db: Annotated[Session, Depends(get_db)], current_user: CurrentUser):
    resource = get_resource_or_404(db, resource_id)
    assert_permission(current_user, KIND_MODULE[resource.kind], Action.APPROVE, db)
    publish(db, resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.post("/automation/{kind}/{key}/rollback/{version}", response_model=ConfigResourceOut)
def generic_rollback(kind: ConfigResourceKind, key: str, version: int, db: Annotated[Session, Depends(get_db)], current_user: CurrentUser):
    assert_permission(current_user, KIND_MODULE[kind], Action.APPROVE, db)
    resource = rollback(db, kind=kind, key=key, target_version=version)
    db.commit()
    db.refresh(resource)
    return resource


# ---- Spec-literal aliases (§09 endpoint list) — thin wrappers over the above ---------

@router.get("/workflows", response_model=list[ConfigResourceOut])
def list_workflows(db: Annotated[Session, Depends(get_db)], _user=require_permission("workflow_builder", Action.READ)):
    return list_current(db, ConfigResourceKind.WORKFLOW)


@router.get("/workflows/runs", response_model=list[WorkflowRunOut])
def list_workflow_runs(db: Annotated[Session, Depends(get_db)], _user=require_permission("workflow_builder", Action.READ)):
    stmt = select(WorkflowRun).options(selectinload(WorkflowRun.actions)).order_by(WorkflowRun.started_at.desc())
    return list(db.execute(stmt).scalars())


@router.post("/workflows/{resource_id}/publish", response_model=ConfigResourceOut)
def publish_workflow(resource_id: uuid.UUID, db: Annotated[Session, Depends(get_db)], _user=require_permission("workflow_builder", Action.APPROVE)):
    resource = get_resource_or_404(db, resource_id)
    if resource.kind != ConfigResourceKind.WORKFLOW:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "Not a workflow.", "field_errors": [], "trace_id": None})
    publish(db, resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.post("/workflows/runs/{run_id}/actions/{action_id}/retry", response_model=WorkflowRunOut)
def retry_workflow_action(
    run_id: uuid.UUID,
    action_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("workflow_builder", Action.WRITE),
):
    action = db.get(WorkflowAction, action_id)
    if action is None or action.run_id != run_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "Workflow action not found.", "field_errors": [], "trace_id": None})
    action.status = WorkflowActionStatus.RETRIED
    action.error_message = None
    action.executed_at = datetime.now(timezone.utc)
    db.commit()

    run = db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id).options(selectinload(WorkflowRun.actions))).scalar_one()
    return run


@router.get("/rules", response_model=list[ConfigResourceOut])
def list_rules(db: Annotated[Session, Depends(get_db)], _user=require_permission("business_rules", Action.READ)):
    return list_current(db, ConfigResourceKind.BUSINESS_RULE)


@router.post("/rules/simulate", response_model=SimulateResult)
def simulate_rule(body: SimulateBody, db: Annotated[Session, Depends(get_db)], _user=require_permission("business_rules", Action.READ)):
    return simulate_business_rule(db, body.when, body.days)


@router.get("/prompts", response_model=list[ConfigResourceOut])
def list_prompts(db: Annotated[Session, Depends(get_db)], _user=require_permission("prompt_management", Action.READ)):
    return list_current(db, ConfigResourceKind.PROMPT_TEMPLATE)


@router.get("/prompts/{resource_id}/versions", response_model=list[ConfigResourceOut])
def prompt_versions(resource_id: uuid.UUID, db: Annotated[Session, Depends(get_db)], _user=require_permission("prompt_management", Action.READ)):
    resource = get_resource_or_404(db, resource_id)
    return list_versions(db, ConfigResourceKind.PROMPT_TEMPLATE, resource.key)


@router.post("/prompts/{resource_id}/rollback", response_model=ConfigResourceOut)
def rollback_prompt(resource_id: uuid.UUID, db: Annotated[Session, Depends(get_db)], _user=require_permission("prompt_management", Action.APPROVE)):
    """`resource_id` is the specific historical version being rolled back TO — reactivate
    it directly rather than looking it up again by version number."""
    resource = get_resource_or_404(db, resource_id)
    if resource.kind != ConfigResourceKind.PROMPT_TEMPLATE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "Not a prompt.", "field_errors": [], "trace_id": None})
    publish(db, resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.get("/routing", response_model=list[ConfigResourceOut])
def list_routing_rules(db: Annotated[Session, Depends(get_db)], _user=require_permission("routing_config", Action.READ)):
    return list_current(db, ConfigResourceKind.ROUTING_RULE)
