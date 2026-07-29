import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.automation import ConfigResourceStatus, WorkflowActionStatus, WorkflowRunStatus


class ConfigResourceOut(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    version: int
    status: ConfigResourceStatus
    config: dict
    description: str | None
    activated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConfigResourceCreate(BaseModel):
    key: str
    name: str
    config: dict
    description: str | None = None


class SimulateBody(BaseModel):
    when: dict
    days: int = 30


class SimulateResult(BaseModel):
    window_days: int
    matched: int
    would_change_outcome: int


class WorkflowActionOut(BaseModel):
    id: uuid.UUID
    action_type: str
    status: WorkflowActionStatus
    error_message: str | None
    executed_at: datetime

    model_config = {"from_attributes": True}


class WorkflowRunOut(BaseModel):
    id: uuid.UUID
    workflow_key: str
    request_id: uuid.UUID | None
    status: WorkflowRunStatus
    started_at: datetime
    finished_at: datetime | None
    actions: list[WorkflowActionOut] = []

    model_config = {"from_attributes": True}
