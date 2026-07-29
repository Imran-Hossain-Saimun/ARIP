import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    id: uuid.UUID
    event_type: str
    actor: str
    object_ref: str
    payload: dict
    prev_hash: str | None
    hash: str
    occurred_at: datetime

    model_config = {"from_attributes": True}


class ChainVerifyResult(BaseModel):
    valid: bool
    event_count: int
    broken_at_id: uuid.UUID | None
