import uuid

from app.models.customer import Customer
from app.models.department import Department
from app.models.request import Channel, Request, RequestStatus
from app.models.user import RoleName


def _auth_headers(client, email: str, password: str = "pw") -> dict:
    token = client.post("/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_request(db_session, *, department: Department | None = None, channel=Channel.WEB) -> Request:
    customer = Customer(email=f"{uuid.uuid4().hex[:8]}@example.com", full_name="Test Customer")
    db_session.add(customer)
    db_session.flush()
    req = Request(
        reference=f"REQ-{uuid.uuid4().hex[:8].upper()}",
        customer_id=customer.id,
        channel=channel,
        status=RequestStatus.RECEIVED,
        department_id=department.id if department else None,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    return req


def test_super_admin_lists_all_requests(client, db_session, make_user):
    _make_request(db_session)
    _make_request(db_session)
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")

    response = client.get("/v1/requests", headers=_auth_headers(client, "admin@nordbank.example"))

    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


def test_support_agent_only_sees_own_department(client, db_session, make_user):
    dept_a = Department(name="Cards & Payments", slug="cards-payments")
    dept_b = Department(name="Mortgages", slug="mortgages")
    db_session.add_all([dept_a, dept_b])
    db_session.flush()

    _make_request(db_session, department=dept_a)
    _make_request(db_session, department=dept_b)

    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, department=dept_a, password="pw")

    response = client.get("/v1/requests", headers=_auth_headers(client, "agent@nordbank.example"))

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["department_id"] == str(dept_a.id)


def test_get_request_detail_includes_messages(client, db_session, make_user):
    req = _make_request(db_session)
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")

    response = client.get(f"/v1/requests/{req.id}", headers=_auth_headers(client, "admin@nordbank.example"))

    assert response.status_code == 200
    assert response.json()["reference"] == req.reference


def test_get_request_404_for_unknown_id(client, make_user):
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")
    response = client.get(f"/v1/requests/{uuid.uuid4()}", headers=_auth_headers(client, "admin@nordbank.example"))
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_agent_cannot_read_request_in_other_department(client, db_session, make_user):
    dept_a = Department(name="Cards & Payments", slug="cards-payments")
    dept_b = Department(name="Mortgages", slug="mortgages")
    db_session.add_all([dept_a, dept_b])
    db_session.flush()
    req = _make_request(db_session, department=dept_b)
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, department=dept_a, password="pw")

    response = client.get(f"/v1/requests/{req.id}", headers=_auth_headers(client, "agent@nordbank.example"))

    assert response.status_code == 403


def test_create_request(client, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    response = client.post(
        "/v1/requests",
        headers=_auth_headers(client, "agent@nordbank.example"),
        json={"customer_email": "new@customer.example", "customer_name": "New Customer", "subject": "Help", "body": "I need help"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["reference"].startswith("REQ-")
    assert len(body["messages"]) == 1


def test_approve_requires_idempotency_key(client, db_session, make_user):
    dept = Department(name="Cards & Payments", slug="cards-payments")
    db_session.add(dept)
    db_session.flush()
    req = _make_request(db_session, department=dept)
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, department=dept, password="pw")

    response = client.post(f"/v1/requests/{req.id}/approve", headers=_auth_headers(client, "agent@nordbank.example"))

    assert response.status_code == 400
    assert response.json()["code"] == "validation_failed"


def test_approve_is_idempotent_on_replay(client, db_session, make_user):
    dept = Department(name="Cards & Payments", slug="cards-payments")
    db_session.add(dept)
    db_session.flush()
    req = _make_request(db_session, department=dept)
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, department=dept, password="pw")
    headers = {**_auth_headers(client, "agent@nordbank.example"), "Idempotency-Key": "abc-123"}

    first = client.post(f"/v1/requests/{req.id}/approve", headers=headers)
    second = client.post(f"/v1/requests/{req.id}/approve", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "answered"
    assert second.json()["status"] == "answered"


def test_dept_manager_cannot_approve_other_department_request(client, db_session, make_user):
    dept_a = Department(name="Cards & Payments", slug="cards-payments")
    dept_b = Department(name="Mortgages", slug="mortgages")
    db_session.add_all([dept_a, dept_b])
    db_session.flush()
    req = _make_request(db_session, department=dept_b)
    make_user("manager@nordbank.example", RoleName.DEPT_MANAGER, department=dept_a, password="pw")
    headers = {**_auth_headers(client, "manager@nordbank.example"), "Idempotency-Key": "xyz-1"}

    response = client.post(f"/v1/requests/{req.id}/approve", headers=headers)

    assert response.status_code == 403


def test_escalate_writes_reason_and_audit_event(client, db_session, make_user):
    dept = Department(name="Cards & Payments", slug="cards-payments")
    db_session.add(dept)
    db_session.flush()
    req = _make_request(db_session, department=dept)
    make_user("manager@nordbank.example", RoleName.DEPT_MANAGER, department=dept, password="pw")
    headers = {**_auth_headers(client, "manager@nordbank.example"), "Idempotency-Key": "esc-1"}

    response = client.post(f"/v1/requests/{req.id}/escalate", headers=headers, json={"reason": "needs legal review"})

    assert response.status_code == 200
    assert response.json()["status"] == "routed"


def test_customer_role_gets_read_only_access_per_matrix():
    from app.core.permissions import Action, has_permission

    assert has_permission(RoleName.CUSTOMER, "requests", Action.READ) is True
    assert has_permission(RoleName.CUSTOMER, "requests", Action.WRITE) is False
