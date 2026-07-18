"""
Regression test: admin API endpoints enforce the role check correctly.

Non-admin user → 403 on all /admin/* endpoints.
Admin user      → 200 (or appropriate non-403) on those same endpoints.

Uses real DB (same pattern as test_ownership_isolation.py): auth.users rows
are created via raw SQL, the FastAPI auth dependency is overridden to return
the test user_id directly, everything downstream (DB, role check) is real.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.auth import get_current_user_id
from app.db.session import engine
from app.main import app


@pytest.fixture
def admin_test_user():
    """A fresh test user with role='admin' in user_tax_personas."""
    user_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO auth.users (id, aud, role, email, created_at, updated_at, is_sso_user, is_anonymous) "
                "VALUES (:id, 'authenticated', 'authenticated', :email, now(), now(), false, false)"
            ),
            {"id": user_id, "email": f"admin-rbac-test-{user_id[:8]}@finvigil.test"},
        )
        conn.execute(
            text(
                "INSERT INTO user_tax_personas (user_id, tax_persona, role, ay_overrides_remaining, is_admin) "
                "VALUES (:uid, 'ITR-3', 'admin', 1, true)"
            ),
            {"uid": user_id},
        )

    yield user_id

    # auth.users FK cascade removes user_tax_personas automatically
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM auth.users WHERE id = :u"), {"u": user_id})


# ── Non-admin blocks ──────────────────────────────────────────────────────────

class TestNonAdminBlocked:
    """A user with no role row (defaults to 'user') must get 403 on every admin endpoint."""

    def _client_for(self, user_id: str) -> TestClient:
        uid = uuid.UUID(user_id)
        app.dependency_overrides[get_current_user_id] = lambda: uid
        return TestClient(app)

    def teardown_method(self):
        app.dependency_overrides.pop(get_current_user_id, None)

    def test_list_users_blocked(self, db_test_user):
        client = self._client_for(db_test_user["user_id"])
        res = client.get("/api/v1/admin/users")
        assert res.status_code == 403
        assert "admin" in res.json()["detail"].lower()

    def test_feature_flags_blocked(self, db_test_user):
        client = self._client_for(db_test_user["user_id"])
        res = client.get("/api/v1/admin/feature-flags")
        assert res.status_code == 403

    def test_audit_logs_blocked(self, db_test_user):
        client = self._client_for(db_test_user["user_id"])
        res = client.get("/api/v1/admin/audit-logs")
        assert res.status_code == 403

    def test_role_change_blocked(self, db_test_user):
        client = self._client_for(db_test_user["user_id"])
        target = str(uuid.uuid4())
        res = client.patch(
            f"/api/v1/admin/users/{target}/role",
            json={"role": "admin"},
        )
        assert res.status_code == 403

    def test_schema_upload_blocked(self, db_test_user):
        client = self._client_for(db_test_user["user_id"])
        res = client.post("/api/v1/admin/itr-schemas", json={})
        assert res.status_code == 403


# ── Admin succeeds ────────────────────────────────────────────────────────────

class TestAdminAllowed:
    """A user with role='admin' must be able to call admin read endpoints."""

    def _client_for(self, user_id: str) -> TestClient:
        uid = uuid.UUID(user_id)
        app.dependency_overrides[get_current_user_id] = lambda: uid
        return TestClient(app)

    def teardown_method(self):
        app.dependency_overrides.pop(get_current_user_id, None)

    def test_list_users_succeeds(self, admin_test_user):
        client = self._client_for(admin_test_user)
        res = client.get("/api/v1/admin/users")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_feature_flags_succeeds(self, admin_test_user):
        client = self._client_for(admin_test_user)
        res = client.get("/api/v1/admin/feature-flags")
        assert res.status_code == 200

    def test_audit_logs_succeeds(self, admin_test_user):
        client = self._client_for(admin_test_user)
        res = client.get("/api/v1/admin/audit-logs")
        assert res.status_code == 200

    def test_schema_upload_allowed(self, admin_test_user):
        # FastAPI resolves auth dependency before parsing the body. Empty body →
        # 422 (Pydantic validation failure) proves the admin passed auth cleanly.
        client = self._client_for(admin_test_user)
        res = client.post("/api/v1/admin/itr-schemas", json={})
        assert res.status_code == 422
