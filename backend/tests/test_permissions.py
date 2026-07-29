import pytest

from app.core.permissions import Action, has_permission
from app.models.user import RoleName


@pytest.mark.parametrize(
    "role,expected",
    [
        (RoleName.SUPER_ADMIN, True),
        (RoleName.ADMIN, True),
        (RoleName.SUPPORT_AGENT, False),
        (RoleName.AUDITOR, True),  # §12: Auditor is read-only everywhere, incl. admin config
        (RoleName.CUSTOMER, False),
    ],
)
def test_admin_users_read_matches_s12_matrix(role, expected):
    assert has_permission(role, "admin_users", Action.READ) is expected


def test_dept_manager_can_approve_but_not_full_reassign_vs_write():
    # §12: dept manager is "A" (approve only) on approve_send, "F" (full) on reassign_escalate.
    assert has_permission(RoleName.DEPT_MANAGER, "approve_send", Action.APPROVE) is True
    assert has_permission(RoleName.DEPT_MANAGER, "approve_send", Action.WRITE) is False
    assert has_permission(RoleName.DEPT_MANAGER, "reassign_escalate", Action.WRITE) is True


def test_auditor_is_read_only_but_full_on_audit_logs():
    assert has_permission(RoleName.AUDITOR, "requests", Action.READ) is True
    assert has_permission(RoleName.AUDITOR, "requests", Action.WRITE) is False
    assert has_permission(RoleName.AUDITOR, "audit_logs", Action.DELETE) is True


class TestAdminDepartmentsEndpoint:
    def test_super_admin_can_list_departments(self, client, make_user):
        make_user("admin@nordbank.example", RoleName.SUPER_ADMIN, password="pw")
        token = client.post("/v1/auth/login", json={"email": "admin@nordbank.example", "password": "pw"}).json()["access_token"]

        response = client.get("/v1/admin/departments", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200

    def test_support_agent_gets_access_denied(self, client, make_user):
        make_user("agent@nordbank.example", RoleName.SUPPORT_AGENT, password="pw")
        token = client.post("/v1/auth/login", json={"email": "agent@nordbank.example", "password": "pw"}).json()["access_token"]

        response = client.get("/v1/admin/departments", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"

    def test_access_denial_writes_an_audit_event(self, client, db_session, make_user):
        # §13 E2E test #4: a denied permission check is itself an auditable event.
        from app.models.audit import AuditEvent

        make_user("exec@nordbank.example", RoleName.EXECUTIVE, password="pw")
        token = client.post("/v1/auth/login", json={"email": "exec@nordbank.example", "password": "pw"}).json()["access_token"]

        response = client.get("/v1/rules", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

        events = db_session.query(AuditEvent).filter(AuditEvent.event_type == "access.denied").all()
        assert len(events) == 1
        assert events[0].actor == "exec@nordbank.example"
        assert events[0].object_ref == "business_rules"
