from pydantic import BaseModel

from app.schemas.analytics import KpiValue


class SlaRiskItem(BaseModel):
    id: str
    reference: str
    subject: str | None
    sla_first_response_due: str | None


class DecisionMixSlice(BaseModel):
    type: str
    count: int


class SystemHealthTile(BaseModel):
    """No real health-check plumbing exists in the app yet (no provider-latency
    tracking, no queue-depth counter) — every field is null until one does."""

    llm_provider_p50_ms: int | None = None
    pgvector_chunk_count: int | None = None
    email_queue_depth: int | None = None
    workflow_workers_healthy: str | None = None


class DashboardSummary(BaseModel):
    role: str
    role_scope: str
    system_health: SystemHealthTile

    # agent / dept_manager
    awaiting_approval_count: int | None = None
    sla_breach_soon: list[SlaRiskItem] | None = None
    decision_mix_24h: list[DecisionMixSlice] | None = None

    # knowledge_manager
    open_gap_count: int | None = None
    top_gap_cluster_key: str | None = None
    top_gap_occurrence_count: int | None = None
    articles_expiring_30d: int | None = None

    # executive
    kpis: list[KpiValue] | None = None

    # auditor
    decision_volume_24h: int | None = None
    override_count_24h: int | None = None
    unresolved_exceptions: int | None = None
