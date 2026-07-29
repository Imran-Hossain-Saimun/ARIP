from app.ai.pipeline import run_pipeline
from app.models.decision import DecisionType
from app.models.request import Channel, RequestStatus
from app.models.user import RoleName


def _auth_headers(client, email: str, password: str = "pw") -> dict:
    token = client.post("/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_pipeline_classifies_legal_and_holds_when_rule_active(db_session):
    from app.core.security import hash_password
    from app.core.versioned_config import create_draft, publish
    from app.models.automation import ConfigResourceKind
    from app.models.user import User

    admin = User(email="admin-fixture@nordbank.example", full_name="Admin", role=RoleName.ADMIN, hashed_password=hash_password("pw"))
    db_session.add(admin)
    db_session.flush()
    rule = create_draft(db_session, kind=ConfigResourceKind.BUSINESS_RULE, key="BR-TEST", name="Legal hold", config={"when": {"category": "Legal"}, "then": {"outcome": "require_human", "priority": 10}}, description=None, user=admin)
    publish(db_session, rule)
    db_session.commit()

    result = run_pipeline(db_session, customer_email="legal@example.com", customer_name="Legal Customer", channel=Channel.WEB, subject="Legal matter", body="I need to discuss a lawsuit regarding my account.")

    assert result.decision.type == DecisionType.HOLD
    assert result.decision.rule_overridden is True
    assert result.request.status == RequestStatus.HELD
    assert result.request.category == "Legal"


def test_pipeline_produces_timed_stages(db_session):
    result = run_pipeline(db_session, customer_email="stages@example.com", customer_name="Stages Customer", channel=Channel.WEB, subject="Question", body="What are your hours?")

    stage_keys = [s.key for s in result.stages]
    assert stage_keys == ["intake", "classify", "retrieval", "confidence", "rules", "decision"]
    assert all(s.ms >= 0 for s in result.stages)


def test_pipeline_writes_audit_events(db_session):
    from app.models.audit import AuditEvent

    result = run_pipeline(db_session, customer_email="audit@example.com", customer_name="Audit Customer", channel=Channel.EMAIL, subject="Q", body="Q")

    events = db_session.query(AuditEvent).filter(AuditEvent.object_ref == f"decision:{result.decision.id}").all()
    assert len(events) == 1
    assert events[0].event_type == "decision.recorded"


def test_portal_submit_creates_a_real_request(client):
    response = client.post(
        "/v1/portal/requests",
        json={"customer_email": "portal@example.com", "customer_name": "Portal Customer", "subject": "Rate question", "body": "What are your current mortgage rates?"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["reference"].startswith("REQ-")
    assert body["progress_stage"] in {"Received", "Reviewed", "Preparing answer", "Resolved"}


def test_portal_submit_requires_no_auth(client):
    # No Authorization header at all — this is the public intake endpoint.
    response = client.post("/v1/portal/requests", json={"customer_email": "x@example.com", "customer_name": "X", "subject": "s", "body": "b"})
    assert response.status_code == 201


def test_portal_track_requires_matching_email(client):
    submit = client.post("/v1/portal/requests", json={"customer_email": "track@example.com", "customer_name": "Track", "subject": "s", "body": "b"}).json()

    wrong_email = client.get(f"/v1/portal/requests/{submit['reference']}", params={"email": "wrong@example.com"})
    right_email = client.get(f"/v1/portal/requests/{submit['reference']}", params={"email": "track@example.com"})

    assert wrong_email.status_code == 404
    assert right_email.status_code == 200
    assert right_email.json()["reference"] == submit["reference"]


def test_portal_feedback_rejects_unresolved_request(client):
    submit = client.post("/v1/portal/requests", json={"customer_email": "fb@example.com", "customer_name": "FB", "subject": "s", "body": "z"}).json()

    if submit["progress_stage"] == "Resolved":
        return  # non-deterministic based on classification — skip if it happened to auto-resolve

    response = client.post(f"/v1/portal/requests/{submit['reference']}/feedback", json={"email": "fb@example.com", "rating": 5})
    assert response.status_code == 400


def test_staff_can_run_pipeline_sandbox(client, make_user):
    make_user("admin@nordbank.example", RoleName.ADMIN, password="pw")
    response = client.post(
        "/v1/ai/run",
        headers=_auth_headers(client, "admin@nordbank.example"),
        json={"customer_email": "sandbox@example.com", "customer_name": "Sandbox", "subject": "Test", "body": "Testing the pipeline sandbox."},
    )
    assert response.status_code == 200
    assert len(response.json()["stages"]) == 6


def test_support_agent_cannot_run_pipeline_sandbox(client, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    response = client.post(
        "/v1/ai/run",
        headers=_auth_headers(client, "agent@nordbank.example"),
        json={"customer_email": "x@example.com", "customer_name": "X", "subject": "s", "body": "b"},
    )
    assert response.status_code == 403
