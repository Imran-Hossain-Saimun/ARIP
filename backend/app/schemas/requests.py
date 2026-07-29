import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.decision import DecisionType
from app.models.request import Channel, MessageAuthor, Priority, RequestStatus


class CustomerOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: uuid.UUID
    author: MessageAuthor
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AttachmentOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int

    model_config = {"from_attributes": True}


class EvidenceOut(BaseModel):
    id: uuid.UUID
    retrieval_mode: str
    score: float
    locator: str
    article_ref: str
    version_ref: str

    model_config = {"from_attributes": True}


class RuleEvaluationOut(BaseModel):
    rule_code: str
    outcome: str
    priority: int

    model_config = {"from_attributes": True}


class DecisionOut(BaseModel):
    id: uuid.UUID
    type: DecisionType
    confidence: float
    threshold: float
    signals: dict
    model: str
    latency_ms: int
    rule_overridden: bool
    created_at: datetime
    evidence: list[EvidenceOut] = []
    rule_evaluations: list[RuleEvaluationOut] = []

    model_config = {"from_attributes": True}


class RequestListItem(BaseModel):
    id: uuid.UUID
    reference: str
    channel: Channel
    status: RequestStatus
    priority: Priority
    intent: str | None
    category: str | None
    department_id: uuid.UUID | None
    assignee_id: uuid.UUID | None
    sla_first_response_due: datetime | None
    created_at: datetime
    customer: CustomerOut
    latest_confidence: float | None = None

    model_config = {"from_attributes": True}


class RequestListResponse(BaseModel):
    items: list[RequestListItem]
    next_cursor: str | None


class RequestDetail(RequestListItem):
    messages: list[MessageOut] = []
    attachments: list[AttachmentOut] = []
    decisions: list[DecisionOut] = []


class RequestCreate(BaseModel):
    customer_email: str
    customer_name: str
    channel: Channel = Channel.WEB
    subject: str
    body: str


class AssignBody(BaseModel):
    assignee_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None


class EscalateBody(BaseModel):
    reason: str
