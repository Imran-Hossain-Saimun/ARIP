import uuid
from datetime import datetime, timedelta, timezone

from app.models.automation import WorkflowAction, WorkflowActionStatus, WorkflowRun, WorkflowRunStatus
from app.models.customer import Customer
from app.models.decision import Decision, DecisionType
from app.models.request import Channel, Priority, Request, RequestStatus
from app.models.user import RoleName


def _auth_headers(client, email: str, password: str = "pw") -> dict:
    token = client.post("/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_create_and_list_a_business_rule_draft(client, make_user):
    make_user("admin@nordbank.example", RoleName.ADMIN, password="pw")
    headers = _auth_headers(client, "admin@nordbank.example")

    response = client.post(
        "/v1/automation/business_rule",
        headers=headers,
        json={"key": "BR-100", "name": "Legal always held", "config": {"when": {"category": "Legal"}, "then": {"outcome": "require_human"}}},
    )

    assert response.status_code == 201
    assert response.json()["version"] == 1
    assert response.json()["status"] == "draft"

    listed = client.get("/v1/rules", headers=headers).json()
    assert any(r["key"] == "BR-100" for r in listed)


def test_support_agent_cannot_create_a_business_rule(client, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    response = client.post(
        "/v1/automation/business_rule",
        headers=_auth_headers(client, "agent@nordbank.example"),
        json={"key": "BR-101", "name": "Should fail", "config": {}},
    )
    assert response.status_code == 403


def test_publish_activates_and_archives_the_previous_version(client, make_user):
    make_user("admin@nordbank.example", RoleName.ADMIN, password="pw")
    headers = _auth_headers(client, "admin@nordbank.example")

    v1 = client.post("/v1/automation/business_rule", headers=headers, json={"key": "BR-200", "name": "v1", "config": {"when": {}}}).json()
    client.post(f"/v1/automation/{v1['id']}/publish", headers=headers)

    v2 = client.post("/v1/automation/business_rule", headers=headers, json={"key": "BR-200", "name": "v2", "config": {"when": {}}}).json()
    publish_v2 = client.post(f"/v1/automation/{v2['id']}/publish", headers=headers)

    assert publish_v2.status_code == 200
    assert publish_v2.json()["status"] == "active"

    versions = client.get("/v1/automation/business_rule/BR-200/versions", headers=headers).json()
    by_version = {v["version"]: v for v in versions}
    assert by_version[1]["status"] == "archived"
    assert by_version[2]["status"] == "active"


def test_rollback_reactivates_an_older_version(client, make_user):
    make_user("admin@nordbank.example", RoleName.ADMIN, password="pw")
    headers = _auth_headers(client, "admin@nordbank.example")

    v1 = client.post("/v1/automation/business_rule", headers=headers, json={"key": "BR-300", "name": "v1", "config": {}}).json()
    client.post(f"/v1/automation/{v1['id']}/publish", headers=headers)
    v2 = client.post("/v1/automation/business_rule", headers=headers, json={"key": "BR-300", "name": "v2 - bad change", "config": {}}).json()
    client.post(f"/v1/automation/{v2['id']}/publish", headers=headers)

    response = client.post("/v1/automation/business_rule/BR-300/rollback/1", headers=headers)

    assert response.status_code == 200
    assert response.json()["version"] == 1
    assert response.json()["status"] == "active"

    versions = client.get("/v1/automation/business_rule/BR-300/versions", headers=headers).json()
    by_version = {v["version"]: v for v in versions}
    assert by_version[1]["status"] == "active"
    assert by_version[2]["status"] == "archived"


def test_simulate_counts_matching_decisions_in_the_window(client, db_session, make_user):
    customer = Customer(email="sim@example.com", full_name="Sim Customer")
    db_session.add(customer)
    db_session.flush()
    req = Request(reference=f"REQ-{uuid.uuid4().hex[:8].upper()}", customer_id=customer.id, channel=Channel.WEB, status=RequestStatus.RECEIVED, category="Legal", priority=Priority.HIGH)
    db_session.add(req)
    db_session.flush()
    db_session.add(Decision(request_id=req.id, type=DecisionType.AUTO_REPLY, confidence=0.97, threshold=0.95, signals={}, stages=[], model="test", latency_ms=10, rule_overridden=False))
    db_session.commit()

    make_user("admin@nordbank.example", RoleName.ADMIN, password="pw")
    response = client.post(
        "/v1/rules/simulate",
        headers=_auth_headers(client, "admin@nordbank.example"),
        json={"when": {"category": "Legal"}, "days": 30},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["matched"] == 1
    assert body["would_change_outcome"] == 1


def test_prompt_versions_and_rollback_use_the_literal_endpoints(client, make_user):
    # §12: knowledge_manager is "W" (draft) on prompt_management, not "A"/"F" — only
    # admin/super_admin can approve/publish/rollback.
    make_user("mei@nordbank.example", RoleName.KNOWLEDGE_MANAGER, password="pw")
    author_headers = _auth_headers(client, "mei@nordbank.example")
    make_user("admin@nordbank.example", RoleName.ADMIN, password="pw")
    approver_headers = _auth_headers(client, "admin@nordbank.example")

    v1 = client.post("/v1/automation/prompt_template", headers=author_headers, json={"key": "reply_prompt", "name": "v1", "config": {"text": "Answer using {{context}}"}}).json()
    client.post(f"/v1/automation/{v1['id']}/publish", headers=approver_headers)
    v2 = client.post("/v1/automation/prompt_template", headers=author_headers, json={"key": "reply_prompt", "name": "v2", "config": {"text": "Answer concisely using {{context}}"}}).json()
    client.post(f"/v1/automation/{v2['id']}/publish", headers=approver_headers)

    versions = client.get(f"/v1/prompts/{v2['id']}/versions", headers=approver_headers).json()
    assert len(versions) == 2

    rollback_response = client.post(f"/v1/prompts/{v1['id']}/rollback", headers=approver_headers)
    assert rollback_response.status_code == 200
    assert rollback_response.json()["version"] == 1
    assert rollback_response.json()["status"] == "active"


def test_dept_manager_cannot_approve_a_prompt_but_knowledge_manager_can():
    from app.core.permissions import Action, has_permission

    assert has_permission(RoleName.KNOWLEDGE_MANAGER, "prompt_management", Action.APPROVE) is False  # §12: "W" not "A"/"F"
    assert has_permission(RoleName.ADMIN, "prompt_management", Action.APPROVE) is True


def test_routing_rules_use_their_own_module(client, make_user):
    make_user("admin@nordbank.example", RoleName.ADMIN, password="pw")
    response = client.post(
        "/v1/automation/routing_rule",
        headers=_auth_headers(client, "admin@nordbank.example"),
        json={"key": "cards_payments_intent", "name": "Card disputes -> Cards & Payments", "config": {"intent": "dispute_charge", "department": "Cards & Payments"}},
    )
    assert response.status_code == 201

    listed = client.get("/v1/routing", headers=_auth_headers(client, "admin@nordbank.example"))
    assert listed.status_code == 200


def test_retry_workflow_action_marks_it_retried(client, db_session, make_user):
    run = WorkflowRun(workflow_key="test_workflow", status=WorkflowRunStatus.FAILED, started_at=datetime.now(timezone.utc) - timedelta(minutes=5))
    db_session.add(run)
    db_session.flush()
    action = WorkflowAction(run_id=run.id, action_type="send_webhook", status=WorkflowActionStatus.FAILED, error_message="timeout", executed_at=datetime.now(timezone.utc))
    db_session.add(action)
    db_session.commit()

    make_user("admin@nordbank.example", RoleName.ADMIN, password="pw")
    response = client.post(f"/v1/workflows/runs/{run.id}/actions/{action.id}/retry", headers=_auth_headers(client, "admin@nordbank.example"))

    assert response.status_code == 200
    retried_action = next(a for a in response.json()["actions"] if a["id"] == str(action.id))
    assert retried_action["status"] == "retried"
    assert retried_action["error_message"] is None
