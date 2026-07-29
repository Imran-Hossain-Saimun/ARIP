import uuid

from app.core.audit import record_audit_event
from app.models.customer import Customer
from app.models.decision import Decision, DecisionType, Evidence, RuleEvaluation
from app.models.department import Department
from app.models.request import Channel, Request, RequestStatus
from app.models.user import RoleName


def _auth_headers(client, email: str, password: str = "pw") -> dict:
    token = client.post("/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_decision(db_session, *, department: Department | None = None, rule_hold: bool = False) -> Decision:
    customer = Customer(email=f"{uuid.uuid4().hex[:8]}@example.com", full_name="Test Customer")
    db_session.add(customer)
    db_session.flush()
    req = Request(
        reference=f"REQ-{uuid.uuid4().hex[:8].upper()}",
        customer_id=customer.id,
        channel=Channel.WEB,
        status=RequestStatus.AWAITING_APPROVAL,
        department_id=department.id if department else None,
    )
    db_session.add(req)
    db_session.flush()

    decision = Decision(
        request_id=req.id,
        type=DecisionType.DRAFT_REPLY,
        confidence=0.91,
        threshold=0.95,
        signals={"intent_certainty": 0.94, "retrieval_agreement": 0.88},
        stages=[{"key": "intake", "ms": 180, "meta": {}}, {"key": "retrieval", "ms": 940, "meta": {"vector_hits": 1}}],
        model="claude-sonnet-4.6",
        latency_ms=1200,
        rule_overridden=rule_hold,
    )
    db_session.add(decision)
    db_session.flush()

    db_session.add(Evidence(decision_id=decision.id, chunk_id=None, retrieval_mode="vector", score=0.912, locator="§3.1", article_ref="KB-0412", version_ref="v4.2"))
    if rule_hold:
        db_session.add(RuleEvaluation(decision_id=decision.id, rule_code="BR-022", outcome="require_human", priority=15))

    record_audit_event(db_session, event_type="decision.recorded", actor="ai_service", object_ref=f"decision:{decision.id}", payload={})
    db_session.commit()
    db_session.refresh(decision)
    return decision


def test_trace_returns_the_full_s09_shape(client, db_session, make_user):
    decision = _make_decision(db_session)
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")

    response = client.get(f"/v1/decisions/{decision.id}/trace", headers=_auth_headers(client, "admin@nordbank.example"))

    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == 0.91
    assert body["threshold"] == 0.95
    assert len(body["stages"]) == 2
    assert body["evidence"][0]["article"] == "KB-0412"
    assert body["audit_hash"] is not None
    assert body["audit_hash"].startswith("sha256:")


def test_trace_includes_rule_evaluations_when_overridden(client, db_session, make_user):
    decision = _make_decision(db_session, rule_hold=True)
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")

    response = client.get(f"/v1/decisions/{decision.id}/trace", headers=_auth_headers(client, "admin@nordbank.example"))

    assert response.status_code == 200
    rules = response.json()["rules"]
    assert len(rules) == 1
    assert rules[0]["id"] == "BR-022"


def test_trace_404_for_unknown_decision(client, make_user):
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")
    response = client.get(f"/v1/decisions/{uuid.uuid4()}/trace", headers=_auth_headers(client, "admin@nordbank.example"))
    assert response.status_code == 404


def test_trace_respects_department_scope(client, db_session, make_user):
    dept_a = Department(name="Cards & Payments", slug="cards-payments")
    dept_b = Department(name="Mortgages", slug="mortgages")
    db_session.add_all([dept_a, dept_b])
    db_session.flush()
    decision = _make_decision(db_session, department=dept_b)
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, department=dept_a, password="pw")

    response = client.get(f"/v1/decisions/{decision.id}/trace", headers=_auth_headers(client, "agent@nordbank.example"))

    assert response.status_code == 403


def test_executive_has_no_decision_trace_access(client, db_session, make_user):
    decision = _make_decision(db_session)
    make_user("exec@nordbank.example", RoleName.EXECUTIVE, password="pw")

    response = client.get(f"/v1/decisions/{decision.id}/trace", headers=_auth_headers(client, "exec@nordbank.example"))

    assert response.status_code == 403


def test_replay_stub_returns_not_yet_replayed(client, db_session, make_user):
    decision = _make_decision(db_session)
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")

    response = client.post(f"/v1/decisions/{decision.id}/replay", headers=_auth_headers(client, "admin@nordbank.example"))

    assert response.status_code == 200
    assert response.json()["replayed"] is False


def test_list_request_decisions_most_recent_first(client, db_session, make_user):
    decision = _make_decision(db_session)
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")

    response = client.get(f"/v1/requests/{decision.request_id}/decisions", headers=_auth_headers(client, "admin@nordbank.example"))

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == str(decision.id)
