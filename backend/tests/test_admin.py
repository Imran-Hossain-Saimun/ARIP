from app.models.user import RoleName


def _auth_headers(client, email: str, password: str = "pw") -> dict:
    token = client.post("/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_create_department(client, make_user):
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")
    response = client.post("/v1/admin/departments", headers=_auth_headers(client, "admin@nordbank.example"), json={"name": "Fraud", "slug": "fraud"})
    assert response.status_code == 201
    assert response.json()["name"] == "Fraud"


def test_admin_can_create_and_list_users(client, make_user):
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")
    headers = _auth_headers(client, "admin@nordbank.example")

    response = client.post(
        "/v1/admin/users",
        headers=headers,
        json={"email": "new.agent@nordbank.example", "full_name": "New Agent", "role": "support_agent", "password": "temp-password-123"},
    )
    assert response.status_code == 201

    listed = client.get("/v1/admin/users", headers=headers).json()
    assert any(u["email"] == "new.agent@nordbank.example" for u in listed)


def test_create_user_rejects_duplicate_email(client, make_user):
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")
    headers = _auth_headers(client, "admin@nordbank.example")
    body = {"email": "dup@nordbank.example", "full_name": "Dup", "role": "support_agent", "password": "temp-password-123"}

    client.post("/v1/admin/users", headers=headers, json=body)
    response = client.post("/v1/admin/users", headers=headers, json=body)

    assert response.status_code == 400
    assert response.json()["code"] == "validation_failed"


def test_update_user_deactivates(client, make_user):
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")
    headers = _auth_headers(client, "admin@nordbank.example")
    agent = make_user("agent2@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")

    response = client.patch(f"/v1/admin/users/{agent.id}", headers=headers, json={"is_active": False})

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_dept_manager_cannot_create_users(client, make_user):
    make_user("manager@nordbank.example", RoleName.DEPT_MANAGER, password="pw")
    response = client.post(
        "/v1/admin/users",
        headers=_auth_headers(client, "manager@nordbank.example"),
        json={"email": "x@nordbank.example", "full_name": "X", "role": "support_agent", "password": "temp-password-123"},
    )
    assert response.status_code == 403
