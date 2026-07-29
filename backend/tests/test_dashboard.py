import uuid
from datetime import date, datetime, timedelta, timezone

from app.models.customer import Customer
from app.models.decision import Decision, DecisionType
from app.models.knowledge import KnowledgeArticle, KnowledgeGap, KnowledgeGapStatus, KnowledgeVersion, KnowledgeVersionStatus
from app.models.request import Channel, Message, MessageAuthor, Request, RequestStatus
from app.models.user import RoleName


def _auth_headers(client, email: str, password: str = "pw") -> dict:
    token = client.post("/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_request(db_session, status: RequestStatus, sla_due=None) -> Request:
    customer = Customer(email=f"{uuid.uuid4().hex[:8]}@example.com", full_name="Test Customer")
    db_session.add(customer)
    db_session.flush()
    req = Request(reference=f"REQ-{uuid.uuid4().hex[:8].upper()}", customer_id=customer.id, channel=Channel.WEB, status=status, sla_first_response_due=sla_due)
    db_session.add(req)
    db_session.flush()
    db_session.add(Message(request_id=req.id, author=MessageAuthor.CUSTOMER, body="hello"))
    db_session.commit()
    return req


def test_agent_sees_approval_and_sla_tiles(client, db_session, make_user):
    due = datetime.now(timezone.utc) + timedelta(minutes=10)
    _make_request(db_session, RequestStatus.AWAITING_APPROVAL, sla_due=due)
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")

    response = client.get("/v1/dashboard/summary", headers=_auth_headers(client, "agent@nordbank.example"))

    assert response.status_code == 200
    body = response.json()
    assert body["awaiting_approval_count"] == 1
    assert len(body["sla_breach_soon"]) == 1
    assert body["kpis"] is None
    assert body["open_gap_count"] is None


def test_knowledge_manager_sees_gap_and_expiry_tiles(client, db_session, make_user):
    gap = KnowledgeGap(cluster_key="card_dispute_duplicate", occurrence_count=34, avg_confidence=0.41, status=KnowledgeGapStatus.OPEN, sample_request_refs=[])
    db_session.add(gap)
    article = KnowledgeArticle(title="Card disputes")
    db_session.add(article)
    db_session.flush()
    db_session.add(
        KnowledgeVersion(
            article_id=article.id,
            version="v1.0",
            status=KnowledgeVersionStatus.APPROVED,
            effective_from=date.today(),
            expires_on=date.today() + timedelta(days=10),
            content="text",
        )
    )
    db_session.commit()
    make_user("mei@nordbank.example", RoleName.KNOWLEDGE_MANAGER, password="pw")

    response = client.get("/v1/dashboard/summary", headers=_auth_headers(client, "mei@nordbank.example"))

    assert response.status_code == 200
    body = response.json()
    assert body["open_gap_count"] == 1
    assert body["top_gap_cluster_key"] == "card_dispute_duplicate"
    assert body["articles_expiring_30d"] == 1
    assert body["awaiting_approval_count"] is None


def test_executive_sees_kpi_tiles(client, db_session, make_user):
    _make_request(db_session, RequestStatus.ANSWERED)
    make_user("exec@nordbank.example", RoleName.EXECUTIVE, password="pw")

    response = client.get("/v1/dashboard/summary", headers=_auth_headers(client, "exec@nordbank.example"))

    assert response.status_code == 200
    body = response.json()
    assert {k["key"] for k in body["kpis"]} == {"BO-001", "BO-002", "BO-003", "BO-004", "BO-005"}


def test_auditor_sees_override_and_exception_tiles(client, db_session, make_user):
    held = _make_request(db_session, RequestStatus.HELD)
    db_session.add(Decision(request_id=held.id, type=DecisionType.HOLD, confidence=0.9, threshold=0.95, signals={}, stages=[], model="test", latency_ms=10, rule_overridden=True))
    db_session.commit()
    make_user("audrey@nordbank.example", RoleName.AUDITOR, password="pw")

    response = client.get("/v1/dashboard/summary", headers=_auth_headers(client, "audrey@nordbank.example"))

    assert response.status_code == 200
    body = response.json()
    assert body["decision_volume_24h"] == 1
    assert body["override_count_24h"] == 1
    assert body["unresolved_exceptions"] == 1


def test_customer_role_denied(client, make_user):
    make_user("cust@nordbank.example", RoleName.CUSTOMER, password="pw")
    response = client.get("/v1/dashboard/summary", headers=_auth_headers(client, "cust@nordbank.example"))
    assert response.status_code == 403
