from app.core.audit import record_audit_event
from app.models.user import RoleName


def _auth_headers(client, email: str, password: str = "pw") -> dict:
    token = client.post("/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_auditor_can_list_and_filter_events(client, db_session, make_user):
    record_audit_event(db_session, event_type="request.created", actor="seed", object_ref="request:1", payload={})
    record_audit_event(db_session, event_type="knowledge.approved", actor="seed", object_ref="knowledge_version:1", payload={})
    db_session.commit()
    make_user("ken@nordbank.example", RoleName.AUDITOR, password="pw")

    response = client.get("/v1/audit", headers=_auth_headers(client, "ken@nordbank.example"), params={"type": "request.created"})

    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "request.created"


def test_support_agent_cannot_view_audit_log(client, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    response = client.get("/v1/audit", headers=_auth_headers(client, "agent@nordbank.example"))
    assert response.status_code == 403


def test_chain_verifies_clean_after_normal_writes(client, db_session, make_user):
    record_audit_event(db_session, event_type="a", actor="x", object_ref="1", payload={})
    record_audit_event(db_session, event_type="b", actor="x", object_ref="2", payload={})
    db_session.commit()
    make_user("ken@nordbank.example", RoleName.AUDITOR, password="pw")

    response = client.get("/v1/audit/verify", headers=_auth_headers(client, "ken@nordbank.example"))

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["broken_at_id"] is None


def test_chain_detects_tampering(client, db_session, make_user):
    event = record_audit_event(db_session, event_type="a", actor="x", object_ref="1", payload={})
    db_session.commit()

    event.payload = {"tampered": True}  # bypasses record_audit_event — simulates DB tampering
    db_session.commit()

    make_user("ken@nordbank.example", RoleName.AUDITOR, password="pw")
    response = client.get("/v1/audit/verify", headers=_auth_headers(client, "ken@nordbank.example"))

    body = response.json()
    assert body["valid"] is False
    assert body["broken_at_id"] == str(event.id)


def test_export_returns_events_in_chain_order(client, db_session, make_user):
    record_audit_event(db_session, event_type="a", actor="x", object_ref="1", payload={})
    record_audit_event(db_session, event_type="b", actor="x", object_ref="2", payload={})
    db_session.commit()
    make_user("ken@nordbank.example", RoleName.AUDITOR, password="pw")

    response = client.get("/v1/audit/export", headers=_auth_headers(client, "ken@nordbank.example"))

    events = response.json()
    assert [e["event_type"] for e in events] == ["a", "b"]
    assert events[1]["prev_hash"] == events[0]["hash"]
