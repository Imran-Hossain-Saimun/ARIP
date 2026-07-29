import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.email import MailboxProvider, MailboxStatus


class MailboxOut(BaseModel):
    id: uuid.UUID
    name: str
    email_address: str
    provider: MailboxProvider
    department_id: uuid.UUID | None
    status: MailboxStatus
    last_synced_at: datetime | None

    model_config = {"from_attributes": True}


class MailboxCreate(BaseModel):
    name: str
    email_address: str
    provider: MailboxProvider = MailboxProvider.MAILHOG
    department_id: uuid.UUID | None = None


class SyncResult(BaseModel):
    created: int
    threaded: int
    failed: int


class ParseFailureOut(BaseModel):
    id: uuid.UUID
    mailbox_id: uuid.UUID
    raw_subject: str | None
    raw_from: str | None
    error_message: str
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}
