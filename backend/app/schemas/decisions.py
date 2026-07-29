from pydantic import BaseModel


class TraceEvidence(BaseModel):
    chunk_id: str | None
    article: str
    version: str
    locator: str
    mode: str
    score: float


class TraceRule(BaseModel):
    id: str
    outcome: str
    priority: int


class TraceStage(BaseModel):
    key: str
    ms: int
    meta: dict


class DecisionTrace(BaseModel):
    """Exact shape from §09 — the frontend's DecisionTraceDrawer consumes this verbatim."""

    decision_id: str
    request_id: str
    type: str
    confidence: float
    threshold: float
    signals: dict
    stages: list[TraceStage]
    evidence: list[TraceEvidence]
    rules: list[TraceRule]
    model: str
    prompt_version: str | None
    audit_hash: str | None


class ReplayResult(BaseModel):
    decision_id: str
    replayed: bool
    message: str
