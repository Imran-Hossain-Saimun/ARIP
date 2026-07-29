from app.models.user import RoleName


def test_login_succeeds_with_correct_credentials(client, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="correct-horse")

    response = client.post("/v1/auth/login", json={"email": "agent@nordbank.example", "password": "correct-horse"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_rejects_wrong_password(client, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="correct-horse")

    response = client.post("/v1/auth/login", json={"email": "agent@nordbank.example", "password": "wrong"})

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_login_rejects_unknown_email(client):
    response = client.post("/v1/auth/login", json={"email": "nobody@nordbank.example", "password": "whatever"})
    assert response.status_code == 401


def test_me_requires_a_token(client):
    response = client.get("/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_the_authenticated_user(client, make_user):
    user = make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="correct-horse")
    token = client.post("/v1/auth/login", json={"email": "agent@nordbank.example", "password": "correct-horse"}).json()["access_token"]

    response = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["role"] == "support_agent"
