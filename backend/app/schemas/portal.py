from pydantic import BaseModel

from app.models.request import Channel


class PortalSubmitRequest(BaseModel):
    customer_email: str
    customer_name: str
    category_hint: str | None = None
    subject: str
    body: str


class PortalSubmitResponse(BaseModel):
    reference: str
    status: str
    progress_stage: str
    ai_message: str | None
    citations: list[str]


class PortalMessageOut(BaseModel):
    author: str
    body: str


class PortalTrackResponse(BaseModel):
    reference: str
    status: str
    progress_stage: str
    channel: Channel
    messages: list[PortalMessageOut]


class PortalFeedbackRequest(BaseModel):
    email: str
    rating: int
    comment: str | None = None
