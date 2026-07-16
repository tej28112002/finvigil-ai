"""
Shared pytest fixtures for backend/tests/.

Two categories of test in this suite:
  - Pure unit tests (tests/fakes.py) — no DB, no network, fast, run always.
  - Integration tests — hit the real Supabase DB via app.db.session.engine.
    These either (a) read the documented primary test user's EXISTING data
    read-only (never mutate it), or (b) create a dedicated, disposable test
    user via the `db_test_user` fixture below and clean it up automatically,
    even on failure. Neither path ever writes to or deletes the primary
    test user's rows.
"""
import uuid

import pytest
from sqlalchemy import text

from app.db.session import engine

PRIMARY_TEST_USER = "765984b3-fd6b-4091-8d24-6808d8680b3a"
RELIANCE_INSTRUMENT_ID = "0e622c58-467d-40bc-9291-d9e11f3f9205"


@pytest.fixture
def db_test_user():
    """
    A fresh, disposable user + broker_connection for tests that need to
    write real trades/holding_lots against the real DB. Same raw-SQL
    creation pattern as tests/test_ownership_isolation.py's seed_user_b()
    (auth.users needs no password/confirmation here since tests call the
    service layer directly, never sign in as this user). Tears itself down
    in every case, including test failure.
    """
    user_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO auth.users (id, aud, role, email, created_at, updated_at, is_sso_user, is_anonymous) "
                "VALUES (:id, 'authenticated', 'authenticated', :email, now(), now(), false, false)"
            ),
            {"id": user_id, "email": f"phase15-fifo-test-{user_id[:8]}@finvigil.test"},
        )
        broker_id = str(uuid.uuid4())
        conn.execute(
            text(
                "INSERT INTO broker_connections (id, user_id, broker_name, status, created_at, updated_at) "
                "VALUES (:id, :uid, 'csv', 'active', now(), now())"
            ),
            {"id": broker_id, "uid": user_id},
        )

    yield {"user_id": user_id, "broker_connection_id": broker_id}

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM realized_gains WHERE user_id = :u"), {"u": user_id})
        conn.execute(text("DELETE FROM holding_lots WHERE user_id = :u"), {"u": user_id})
        conn.execute(text("DELETE FROM trades WHERE user_id = :u"), {"u": user_id})
        conn.execute(text("DELETE FROM tax_summaries WHERE user_id = :u"), {"u": user_id})
        conn.execute(text("DELETE FROM broker_connections WHERE user_id = :u"), {"u": user_id})
        conn.execute(text("DELETE FROM auth.users WHERE id = :u"), {"u": user_id})


@pytest.fixture
def db_session():
    """A real SQLAlchemy session against the real DB, rolled back after each test."""
    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
