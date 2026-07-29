from app.models.knowledge import KnowledgeGap, KnowledgeGapStatus
from app.models.user import RoleName


def _auth_headers(client, email: str, password: str = "pw") -> dict:
    token = client.post("/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_knowledge_manager_can_ingest_a_text_article(client, make_user):
    make_user("mei@nordbank.example", RoleName.KNOWLEDGE_MANAGER, password="pw")
    headers = _auth_headers(client, "mei@nordbank.example")

    response = client.post(
        "/v1/knowledge/ingest",
        headers=headers,
        data={"title": "Card dispute policy", "version": "v1.0", "content": "# Card disputes\nRefunds take 5-7 business days."},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["article_id"]
    assert body["version_id"]


def test_ingest_requires_some_text_content(client, make_user):
    make_user("mei@nordbank.example", RoleName.KNOWLEDGE_MANAGER, password="pw")
    headers = _auth_headers(client, "mei@nordbank.example")

    response = client.post("/v1/knowledge/ingest", headers=headers, data={"title": "Empty article"})

    assert response.status_code == 400
    assert response.json()["code"] == "validation_failed"


def test_support_agent_cannot_ingest_knowledge(client, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    headers = _auth_headers(client, "agent@nordbank.example")

    response = client.post("/v1/knowledge/ingest", headers=headers, data={"title": "Should fail", "content": "text"})

    assert response.status_code == 403


def test_new_version_starts_as_draft_and_list_shows_it(client, make_user):
    make_user("mei@nordbank.example", RoleName.KNOWLEDGE_MANAGER, password="pw")
    headers = _auth_headers(client, "mei@nordbank.example")
    client.post("/v1/knowledge/ingest", headers=headers, data={"title": "Loan policy", "version": "v1.0", "content": "Some loan policy text."})

    response = client.get("/v1/knowledge", headers=headers)

    assert response.status_code == 200
    articles = response.json()
    loan = next(a for a in articles if a["title"] == "Loan policy")
    assert loan["latest_version"]["status"] == "draft"


def test_approve_transitions_to_indexed_and_creates_chunks(client, make_user, db_session):
    make_user("mei@nordbank.example", RoleName.KNOWLEDGE_MANAGER, password="pw")
    headers = _auth_headers(client, "mei@nordbank.example")
    ingest = client.post(
        "/v1/knowledge/ingest",
        headers=headers,
        data={"title": "KYC policy", "version": "v1.0", "content": "# KYC\nUpload your documents within 30 days."},
    ).json()

    response = client.post(f"/v1/knowledge/{ingest['article_id']}/versions/v1.0/approve", headers=headers, json={})

    assert response.status_code == 200
    assert response.json()["status"] == "indexed"
    assert response.json()["indexed_at"] is not None


def test_support_agent_cannot_approve_knowledge(client, make_user):
    # §12: knowledge_approval is "-" (no access) for support_agent, vs. "A" for dept_manager.
    make_user("mei@nordbank.example", RoleName.KNOWLEDGE_MANAGER, password="pw")
    ingest = client.post(
        "/v1/knowledge/ingest",
        headers=_auth_headers(client, "mei@nordbank.example"),
        data={"title": "Restricted approval test", "version": "v1.0", "content": "text"},
    ).json()

    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    response = client.post(
        f"/v1/knowledge/{ingest['article_id']}/versions/v1.0/approve",
        headers=_auth_headers(client, "agent@nordbank.example"),
        json={},
    )

    assert response.status_code == 403


def test_list_gaps_ranked_by_occurrence(client, db_session, make_user):
    db_session.add(KnowledgeGap(cluster_key="login_issue", occurrence_count=5, avg_confidence=0.4, status=KnowledgeGapStatus.OPEN, sample_request_refs=["REQ-1"]))
    db_session.add(KnowledgeGap(cluster_key="rate_question", occurrence_count=34, avg_confidence=0.41, status=KnowledgeGapStatus.OPEN, sample_request_refs=["REQ-2"]))
    db_session.commit()
    make_user("mei@nordbank.example", RoleName.KNOWLEDGE_MANAGER, password="pw")

    response = client.get("/v1/gaps", headers=_auth_headers(client, "mei@nordbank.example"))

    assert response.status_code == 200
    keys = [g["cluster_key"] for g in response.json()]
    assert keys == ["rate_question", "login_issue"]
