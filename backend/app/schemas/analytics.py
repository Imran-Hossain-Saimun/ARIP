from pydantic import BaseModel


class KpiValue(BaseModel):
    key: str
    label: str
    value: float | None
    target: float | None
    unit: str


class FunnelStage(BaseModel):
    type: str
    count: int


class CitedArticle(BaseModel):
    article_ref: str
    citation_count: int


class AnalyticsKpis(BaseModel):
    window_days: int
    kpis: list[KpiValue]
    automation_funnel: list[FunnelStage]
    most_cited_knowledge: list[CitedArticle]
