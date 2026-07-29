from app.models.department import Department
from app.models.user import RoleName


def test_any_authenticated_role_can_list_departments_for_pickers(client, db_session, make_user):
    db_session.add(Department(name="Cards & Payments", slug="cards-payments"))
    db_session.commit()
    make_user("mei@nordbank.example", RoleName.KNOWLEDGE_MANAGER, password="pw")
    token = client.post("/v1/auth/login", json={"email": "mei@nordbank.example", "password": "pw"}).json()["access_token"]

    response = client.get("/v1/departments", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Cards & Payments"


def test_unauthenticated_cannot_list_departments(client):
    response = client.get("/v1/departments")
    assert response.status_code == 401
