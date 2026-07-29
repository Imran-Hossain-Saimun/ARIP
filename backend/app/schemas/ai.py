import uuid

from pydantic import BaseModel

from app.models.request import Channel


class RunPipelineRequest(BaseModel):
    customer_email: str
    customer_name: str
    channel: Channel = Channel.WEB
    subject: str
    body: str


class PipelineStageOut(BaseModel):
    key: str
    ms: int
    meta: dict


class RunPipelineResponse(BaseModel):
    request_id: uuid.UUID
    reference: str
    decision_id: uuid.UUID
    decision_type: str
    confidence: float
    rule_overridden: bool
    stages: list[PipelineStageOut]
