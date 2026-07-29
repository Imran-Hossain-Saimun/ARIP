from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.permissions import Action, require_permission
from app.models.decision import Decision, DecisionType, Evidence
from app.models.feedback import Feedback
from app.models.request import Message, MessageAuthor, Request
from app.schemas.analytics import AnalyticsKpis, CitedArticle, FunnelStage, KpiValue

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])


@router.get("/kpis", response_model=AnalyticsKpis)
def get_kpis(
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("analytics", Action.READ),
    days: int = Query(30, alias="range"),
) -> AnalyticsKpis:
    """BO-001..BO-005 from the BRD. Several of these are necessarily approximated — the
    seed data doesn't carry a ground-truth "was this the right department" signal, for
    instance — see the per-KPI comments and the task doc's Delivered notes."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    total_decisions = db.execute(select(func.count()).select_from(Decision).where(Decision.created_at >= since)).scalar() or 0
    automated_decisions = db.execute(
        select(func.count()).select_from(Decision).where(Decision.created_at >= since, Decision.type.in_([DecisionType.AUTO_REPLY, DecisionType.DRAFT_REPLY]))
    ).scalar() or 0
    routed_decisions = db.execute(select(func.count()).select_from(Decision).where(Decision.created_at >= since, Decision.type == DecisionType.ROUTE)).scalar() or 0

    # First-response time: minutes between a request's creation and its first non-customer message.
    first_response_subq = (
        select(func.min(Message.created_at))
        .where(Message.request_id == Request.id, Message.author != MessageAuthor.CUSTOMER)
        .correlate(Request)
        .scalar_subquery()
    )
    requests_with_response = db.execute(
        select(Request.created_at, first_response_subq.label("first_response")).where(Request.created_at >= since)
    ).all()
    response_minutes = [
        (first_response - created).total_seconds() / 60 for created, first_response in requests_with_response if first_response is not None
    ]
    avg_response_minutes = sum(response_minutes) / len(response_minutes) if response_minutes else None

    citation_count = db.execute(select(func.count()).select_from(Evidence).join(Decision, Evidence.decision_id == Decision.id).where(Decision.created_at >= since)).scalar() or 0

    avg_csat = db.execute(select(func.avg(Feedback.rating)).where(Feedback.created_at >= since)).scalar()

    kpis = [
        KpiValue(key="BO-001", label="Manual effort reduction", value=round(automated_decisions / total_decisions, 3) if total_decisions else None, target=0.70, unit="ratio"),
        # Proxy: share of decisions the AI resolved without routing to a human department.
        KpiValue(key="BO-002", label="Routing accuracy (proxy)", value=round(1 - routed_decisions / total_decisions, 3) if total_decisions else None, target=0.95, unit="ratio"),
        KpiValue(key="BO-003", label="First response time", value=round(avg_response_minutes, 1) if avg_response_minutes is not None else None, target=None, unit="minutes"),
        KpiValue(key="BO-004", label="Knowledge reuse (citations)", value=float(citation_count), target=None, unit="count"),
        KpiValue(key="BO-005", label="Customer satisfaction", value=round(float(avg_csat), 2) if avg_csat is not None else None, target=None, unit="stars (1-5)"),
    ]

    funnel_rows = db.execute(
        select(Decision.type, func.count()).where(Decision.created_at >= since).group_by(Decision.type)
    ).all()
    funnel = [FunnelStage(type=t.value, count=c) for t, c in funnel_rows]

    cited_rows = db.execute(
        select(Evidence.article_ref, func.count())
        .join(Decision, Evidence.decision_id == Decision.id)
        .where(Decision.created_at >= since)
        .group_by(Evidence.article_ref)
        .order_by(func.count().desc())
        .limit(5)
    ).all()
    most_cited = [CitedArticle(article_ref=ref, citation_count=count) for ref, count in cited_rows]

    return AnalyticsKpis(window_days=days, kpis=kpis, automation_funnel=funnel, most_cited_knowledge=most_cited)
