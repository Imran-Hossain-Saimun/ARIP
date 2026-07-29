from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.router import compute_kpis
from app.core.db import get_db
from app.core.permissions import Action, is_department_scoped, require_permission
from app.core.security import CurrentUser
from app.models.decision import Decision
from app.models.knowledge import KnowledgeGap, KnowledgeGapStatus, KnowledgeVersion, KnowledgeVersionStatus
from app.models.request import Request, RequestStatus
from app.models.user import RoleName
from app.schemas.dashboard import DashboardSummary, DecisionMixSlice, SlaRiskItem, SystemHealthTile

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])

# §07 lifecycle states that mean "someone still owes this request a resolution" — used
# as the auditor's unresolved-exceptions proxy. No dedicated "exception" concept exists
# in the data model, so this mirrors the BO-002 proxy pattern in app/analytics/router.py.
_UNRESOLVED_STATUSES = (RequestStatus.HELD, RequestStatus.ROUTED, RequestStatus.AWAITING_APPROVAL)


def _department_scoped_requests(db: Session, current_user: CurrentUser):
    stmt = select(Request)
    if is_department_scoped(current_user.role):
        stmt = stmt.where(Request.department_id == current_user.department_id)
    return stmt


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user=require_permission("dashboard", Action.READ),
) -> DashboardSummary:
    role_scope = current_user.department.name if current_user.department else "All departments"
    summary = DashboardSummary(role=current_user.role.value, role_scope=role_scope, system_health=SystemHealthTile())

    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    if current_user.role in (RoleName.SUPPORT_AGENT, RoleName.DEPT_MANAGER, RoleName.ADMIN, RoleName.SUPER_ADMIN):
        base = _department_scoped_requests(db, current_user)

        summary.awaiting_approval_count = db.execute(
            select(func.count()).select_from(base.where(Request.status == RequestStatus.AWAITING_APPROVAL).subquery())
        ).scalar() or 0

        risk_rows = db.execute(
            base.where(Request.sla_first_response_due.is_not(None))
            .order_by(Request.sla_first_response_due.asc())
            .limit(3)
        ).scalars()
        summary.sla_breach_soon = [
            SlaRiskItem(
                id=str(r.id),
                reference=r.reference,
                subject=(r.messages[0].body[:80] if r.messages else None),
                sla_first_response_due=r.sla_first_response_due.isoformat() if r.sla_first_response_due else None,
            )
            for r in risk_rows
        ]

        mix_stmt = select(Decision.type, func.count()).join(Request, Decision.request_id == Request.id).where(Decision.created_at >= since_24h)
        if is_department_scoped(current_user.role):
            mix_stmt = mix_stmt.where(Request.department_id == current_user.department_id)
        mix_rows = db.execute(mix_stmt.group_by(Decision.type)).all()
        summary.decision_mix_24h = [DecisionMixSlice(type=t.value, count=c) for t, c in mix_rows]

    if current_user.role in (RoleName.KNOWLEDGE_MANAGER, RoleName.ADMIN, RoleName.SUPER_ADMIN):
        summary.open_gap_count = db.execute(
            select(func.count()).select_from(KnowledgeGap).where(KnowledgeGap.status == KnowledgeGapStatus.OPEN)
        ).scalar() or 0

        top_gap = db.execute(
            select(KnowledgeGap).where(KnowledgeGap.status == KnowledgeGapStatus.OPEN).order_by(KnowledgeGap.occurrence_count.desc()).limit(1)
        ).scalar_one_or_none()
        if top_gap is not None:
            summary.top_gap_cluster_key = top_gap.cluster_key
            summary.top_gap_occurrence_count = top_gap.occurrence_count

        expiry_cutoff = datetime.now(timezone.utc).date() + timedelta(days=30)
        summary.articles_expiring_30d = db.execute(
            select(func.count())
            .select_from(KnowledgeVersion)
            .where(
                KnowledgeVersion.status.in_([KnowledgeVersionStatus.APPROVED, KnowledgeVersionStatus.INDEXED]),
                KnowledgeVersion.expires_on.is_not(None),
                KnowledgeVersion.expires_on <= expiry_cutoff,
            )
        ).scalar() or 0

    if current_user.role in (RoleName.EXECUTIVE, RoleName.ADMIN, RoleName.SUPER_ADMIN):
        summary.kpis = compute_kpis(db, days=30).kpis

    if current_user.role in (RoleName.AUDITOR, RoleName.ADMIN, RoleName.SUPER_ADMIN):
        summary.decision_volume_24h = db.execute(
            select(func.count()).select_from(Decision).where(Decision.created_at >= since_24h)
        ).scalar() or 0
        summary.override_count_24h = db.execute(
            select(func.count()).select_from(Decision).where(Decision.created_at >= since_24h, Decision.rule_overridden.is_(True))
        ).scalar() or 0
        summary.unresolved_exceptions = db.execute(
            select(func.count()).select_from(Request).where(Request.status.in_(_UNRESOLVED_STATUSES))
        ).scalar() or 0

    return summary
