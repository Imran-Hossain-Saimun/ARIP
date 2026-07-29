import smtplib
import uuid
from email.mime.text import MIMEText

import pytest

from app.models.email import MailboxProvider
from app.models.request import Request
from app.models.user import RoleName


def _auth_headers(client, email: str, password: str = "pw") -> dict:
    token = client.post("/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _mailhog_is_up() -> bool:
    import httpx

    try:
        httpx.get("http://127.0.0.1:8025/api/v2/messages", params={"limit": 1}, timeout=1.0)
        return True
    except httpx.HTTPError:
        return False


requires_mailhog = pytest.mark.skipif(not _mailhog_is_up(), reason="Mailhog isn't running on localhost:8025 (docker compose up -d mailhog)")


def _send_test_email(to_addr: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "customer@example.com"
    msg["To"] = to_addr
    with smtplib.SMTP("127.0.0.1", 1026, timeout=5) as smtp:
        smtp.sendmail("customer@example.com", [to_addr], msg.as_string())


def test_support_agent_can_list_mailboxes(client, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    response = client.get("/v1/email/mailboxes", headers=_auth_headers(client, "agent@nordbank.example"))
    assert response.status_code == 200


def test_knowledge_manager_cannot_access_email(client, make_user):
    # §12: "email" is "-" for knowledge_manager.
    make_user("mei@nordbank.example", RoleName.KNOWLEDGE_MANAGER, password="pw")
    response = client.get("/v1/email/mailboxes", headers=_auth_headers(client, "mei@nordbank.example"))
    assert response.status_code == 403


def test_create_mailbox(client, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    response = client.post(
        "/v1/email/mailboxes",
        headers=_auth_headers(client, "agent@nordbank.example"),
        json={"name": "Support inbox", "email_address": f"support-{uuid.uuid4().hex[:6]}@nordbank.example", "provider": "mailhog"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "disconnected"


def test_sync_rejects_non_mailhog_provider(client, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    headers = _auth_headers(client, "agent@nordbank.example")
    mailbox = client.post(
        "/v1/email/mailboxes",
        headers=headers,
        json={"name": "IMAP inbox", "email_address": f"imap-{uuid.uuid4().hex[:6]}@nordbank.example", "provider": "imap"},
    ).json()

    response = client.post(f"/v1/email/mailboxes/{mailbox['id']}/sync", headers=headers)

    assert response.status_code == 422
    assert response.json()["code"] == "provider_not_supported"


def test_resolve_unknown_parse_failure_404s(client, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    response = client.post(f"/v1/email/parse-failures/{uuid.uuid4()}/resolve", headers=_auth_headers(client, "agent@nordbank.example"))
    assert response.status_code == 404


@requires_mailhog
def test_sync_creates_a_request_from_a_real_email(client, db_session, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    headers = _auth_headers(client, "agent@nordbank.example")
    inbox_address = f"inbox-{uuid.uuid4().hex[:6]}@nordbank.example"
    mailbox = client.post(
        "/v1/email/mailboxes",
        headers=headers,
        json={"name": "Test inbox", "email_address": inbox_address, "provider": "mailhog"},
    ).json()

    _send_test_email(inbox_address, "Question about my statement", "Why was I charged a fee this month?")

    response = client.post(f"/v1/email/mailboxes/{mailbox['id']}/sync", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["created"] >= 1

    created = db_session.query(Request).filter(Request.channel == "email").all()
    assert any(r.channel.value == "email" for r in created)


@requires_mailhog
def test_sync_threads_a_reply_onto_the_existing_request(client, db_session, make_user):
    make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
    headers = _auth_headers(client, "agent@nordbank.example")
    inbox_address = f"inbox-{uuid.uuid4().hex[:6]}@nordbank.example"
    mailbox = client.post(
        "/v1/email/mailboxes",
        headers=headers,
        json={"name": "Thread test inbox", "email_address": inbox_address, "provider": "mailhog"},
    ).json()

    _send_test_email(inbox_address, "Initial question", "First message body")
    client.post(f"/v1/email/mailboxes/{mailbox['id']}/sync", headers=headers)

    created = db_session.query(Request).filter(Request.channel == "email").order_by(Request.created_at.desc()).first()
    assert created is not None

    _send_test_email(inbox_address, f"Re: {created.reference} Initial question", "Follow-up message body")
    response = client.post(f"/v1/email/mailboxes/{mailbox['id']}/sync", headers=headers)

    assert response.json()["threaded"] >= 1
