import uuid

from app.models.customer import Customer
from app.models.decision import Decision, DecisionType
from app.models.request import Channel, MessageAuthor, Message, Request, RequestStatus
from app.models.user import RoleName


def _auth_headers(client, email: str, password: str = "pw") -> dict:
    token = client.post("/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_request_with_decision(db_session, decision_type: DecisionType) -> Request:
    customer = Customer(email=f"{uuid.uuid4().hex[:8]}@example.com", full_name="Test Customer")
    db_session.add(customer)
    db_session.flush()
    req = Request(reference=f"REQ-{uuid.uuid4().hex[:8].upper()}", customer_id=customer.id, channel=Channel.WEB, status=RequestStatus.ANSWERED)
    db_session.add(req)
    db_session.flush()
    db_session.add(Message(request_id=req.id, author=MessageAuthor.CUSTOMER, body="hello"))
    db_session.add(Message(request_id=req.id, author=MessageAuthor.AI, body="reply"))
    db_session.add(Decision(request_id=req.id, type=decision_type, confidence=0.9, threshold=0.95, signals={}, stages=[], model="test", latency_ms=10, rule_overridden=False))
    db_session.commit()
    return req


def test_executive_sees_kpis_with_expected_shape(client, db_session, make_user):
    _make_request_with_decision(db_session, DecisionType.AUTO_REPLY)
    _make_request_with_decision(db_session, DecisionType.ROUTE)
    make_user("exec@nordbank.example", RoleName.EXECUTIVE, password="pw")

    response = client.get("/v1/analytics/kpis", headers=_auth_headers(client, "exec@nordbank.example"))

    assert response.status_code == 200
    body = response.json()
    keys = {k["key"] for k in body["kpis"]}
    assert keys == {"BO-001", "BO-002", "BO-003", "BO-004", "BO-005"}
    bo001 = next(k for k in body["kpis"] if k["key"] == "BO-001")
    assert bo001["value"] == 0.5  # 1 of 2 decisions was automated


def test_support_agent_cannot_view_analytics(client, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    response = client.get("/v1/analytics/kpis", headers=_auth_headers(client, "agent@nordbank.example"))
    assert response.status_code == 403


def test_automation_funnel_groups_by_decision_type(client, db_session, make_user):
    _make_request_with_decision(db_session, DecisionType.AUTO_REPLY)
    _make_request_with_decision(db_session, DecisionType.AUTO_REPLY)
    _make_request_with_decision(db_session, DecisionType.HOLD)
    make_user("exec@nordbank.example", RoleName.EXECUTIVE, password="pw")

    response = client.get("/v1/analytics/kpis", headers=_auth_headers(client, "exec@nordbank.example"))

    funnel = {stage["type"]: stage["count"] for stage in response.json()["automation_funnel"]}
    assert funnel["auto_reply"] == 2
    assert funnel["hold"] == 1
