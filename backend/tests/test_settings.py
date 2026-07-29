from app.models.user import RoleName


def _auth_headers(client, email: str, password: str = "pw") -> dict:
    token = client.post("/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_settings_returns_seeded_defaults(client, make_user):
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")
    response = client.get("/v1/settings", headers=_auth_headers(client, "admin@nordbank.example"))

    assert response.status_code == 200
    keys = {s["key"] for s in response.json()}
    assert "retrieval" in keys
    assert "ai_providers" in keys
    retrieval = next(s for s in response.json() if s["key"] == "retrieval")
    assert retrieval["value"]["chunk_size"] == 800


def test_admin_can_update_a_setting(client, make_user):
    make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")
    headers = _auth_headers(client, "admin@nordbank.example")
    client.get("/v1/settings", headers=headers)  # ensure defaults exist

    response = client.put("/v1/settings/retrieval", headers=headers, json={"value": {"chunk_size": 1000, "overlap": 150}})

    assert response.status_code == 200
    assert response.json()["value"]["chunk_size"] == 1000


def test_support_agent_cannot_update_settings(client, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    response = client.put(
        "/v1/settings/retrieval",
        headers=_auth_headers(client, "agent@nordbank.example"),
        json={"value": {"chunk_size": 1}},
    )
    assert response.status_code == 403
