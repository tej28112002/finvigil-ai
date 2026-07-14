"""
Real, runnable proof that the 3 previously-disclosed ownership-check gaps
are closed:
  GET /holdings/{lot_id}
  GET /trades/{trade_id}
  GET /realized-gains/trade/{sell_trade_id}

Creates a second real user (real row in auth.users, satisfying the FK
constraint that trades/holding_lots/realized_gains have on it) with one
real resource of each type, then makes real HTTP requests through FastAPI's
routing against the real database — the ONLY thing swapped is
get_current_user_id, overridden to return a specific user_id instead of
parsing a Supabase-signed JWT (the standard way to test authenticated
FastAPI endpoints without a real JWKS private key, which can't be forged).
Everything downstream of that one dependency — repository, service, API,
Postgres — is the real, unmodified app.

Cleans up the second user and its seeded rows automatically, even on
failure. Does not touch the primary test user's data.

Run: venv\\Scripts\\python.exe -m tests.test_ownership_isolation
(No pytest dependency — this project has no existing test framework;
requires `httpx` for FastAPI's TestClient, install with `pip install httpx`
if not already present.)
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.core.auth import get_current_user_id
from app.db.session import engine

USER_A = "765984b3-fd6b-4091-8d24-6808d8680b3a"  # the project's documented primary test user


def seed_user_b() -> dict:
    """Real second user + one real trade/holding_lot/realized_gain, via
    direct SQL (only `id` is required with no default on auth.users — no
    password/confirmation needed since this test never signs in as them,
    it calls the app directly with an overridden user_id)."""
    user_b = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO auth.users (id, aud, role, email, created_at, updated_at, is_sso_user, is_anonymous) "
                "VALUES (:id, 'authenticated', 'authenticated', :email, now(), now(), false, false)"
            ),
            {"id": user_b, "email": f"ownership-test-{user_b[:8]}@finvigil.test"},
        )
        broker_id = str(uuid.uuid4())
        conn.execute(
            text(
                "INSERT INTO broker_connections (id, user_id, broker_name, status, created_at, updated_at) "
                "VALUES (:id, :uid, 'csv', 'active', now(), now())"
            ),
            {"id": broker_id, "uid": user_b},
        )
        instrument_id = conn.execute(text("SELECT id FROM instruments LIMIT 1")).scalar()

        trade_id = str(uuid.uuid4())
        conn.execute(
            text(
                "INSERT INTO trades (id, user_id, broker_connection_id, instrument_id, broker_trade_id, "
                "trade_type, quantity, price, execution_time, idempotency_hash, created_at, updated_at) "
                "VALUES (:id, :uid, :bcid, :iid, 'OWNERSHIP-TEST-TRADE', 'buy', 10, 100, now(), :hash, now(), now())"
            ),
            {"id": trade_id, "uid": user_b, "bcid": broker_id, "iid": instrument_id, "hash": f"ownership-test-{trade_id}"},
        )
        lot_id = str(uuid.uuid4())
        conn.execute(
            text(
                "INSERT INTO holding_lots (id, user_id, broker_connection_id, instrument_id, source_trade_id, "
                "quantity_bought, quantity_remaining, buy_price, buy_date, status, created_at, updated_at) "
                "VALUES (:id, :uid, :bcid, :iid, :tid, 10, 10, 100, now(), 'open', now(), now())"
            ),
            {"id": lot_id, "uid": user_b, "bcid": broker_id, "iid": instrument_id, "tid": trade_id},
        )
        sell_trade_id = str(uuid.uuid4())
        conn.execute(
            text(
                "INSERT INTO trades (id, user_id, broker_connection_id, instrument_id, broker_trade_id, "
                "trade_type, quantity, price, execution_time, idempotency_hash, created_at, updated_at) "
                "VALUES (:id, :uid, :bcid, :iid, 'OWNERSHIP-TEST-SELL', 'sell', 5, 120, now(), :hash, now(), now())"
            ),
            {"id": sell_trade_id, "uid": user_b, "bcid": broker_id, "iid": instrument_id, "hash": f"ownership-test-sell-{sell_trade_id}"},
        )
        conn.execute(
            text(
                "INSERT INTO realized_gains (id, user_id, sell_trade_id, holding_lot_id, instrument_id, "
                "quantity_sold, buy_price, sell_price, buy_date, sell_date, holding_days, gain_type, "
                "profit_loss, income_type, created_at, updated_at) "
                "VALUES (:id, :uid, :sell_tid, :lot_id, :iid, 5, 100, 120, now(), now(), 0, 'STCG', 100, "
                "'equity_capital_gains', now(), now())"
            ),
            {"id": str(uuid.uuid4()), "uid": user_b, "sell_tid": sell_trade_id, "lot_id": lot_id, "iid": instrument_id},
        )

    return {"user_id": user_b, "trade_id": trade_id, "lot_id": lot_id, "sell_trade_id": sell_trade_id}


def cleanup_user_b(user_b: str) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM realized_gains WHERE user_id = :u"), {"u": user_b})
        conn.execute(text("DELETE FROM holding_lots WHERE user_id = :u"), {"u": user_b})
        conn.execute(text("DELETE FROM trades WHERE user_id = :u"), {"u": user_b})
        conn.execute(text("DELETE FROM broker_connections WHERE user_id = :u"), {"u": user_b})
        conn.execute(text("DELETE FROM auth.users WHERE id = :u"), {"u": user_b})


def get_user_a_resource_ids() -> dict:
    with engine.connect() as conn:
        return {
            "lot_id": str(conn.execute(text("SELECT id FROM holding_lots WHERE user_id = :u LIMIT 1"), {"u": USER_A}).scalar()),
            "trade_id": str(conn.execute(text("SELECT id FROM trades WHERE user_id = :u LIMIT 1"), {"u": USER_A}).scalar()),
            "sell_trade_id": str(conn.execute(text("SELECT sell_trade_id FROM realized_gains WHERE user_id = :u LIMIT 1"), {"u": USER_A}).scalar()),
        }


def run() -> bool:
    client = TestClient(app)
    results: list[bool] = []

    def as_user(user_id: str) -> None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id

    def check(label: str, resp, expected_status: int) -> None:
        ok = resp.status_code == expected_status
        results.append(ok)
        print(f"  {'PASS' if ok else 'FAIL'}  {label}: HTTP {resp.status_code} (expected {expected_status})")

    a = get_user_a_resource_ids()
    b = seed_user_b()

    try:
        print("=== GET /holdings/{lot_id} ===")
        as_user(USER_A)
        check("User A -> own lot", client.get(f"/api/v1/holdings/{a['lot_id']}"), 200)
        check("User A -> User B's lot (cross-user, must 404 not leak)", client.get(f"/api/v1/holdings/{b['lot_id']}"), 404)
        as_user(b["user_id"])
        check("User B -> own lot", client.get(f"/api/v1/holdings/{b['lot_id']}"), 200)
        check("User B -> User A's lot (cross-user, must 404 not leak)", client.get(f"/api/v1/holdings/{a['lot_id']}"), 404)

        print("\n=== GET /trades/{trade_id} ===")
        as_user(USER_A)
        check("User A -> own trade", client.get(f"/api/v1/trades/{a['trade_id']}"), 200)
        check("User A -> User B's trade (cross-user, must 404 not leak)", client.get(f"/api/v1/trades/{b['trade_id']}"), 404)
        as_user(b["user_id"])
        check("User B -> own trade", client.get(f"/api/v1/trades/{b['trade_id']}"), 200)
        check("User B -> User A's trade (cross-user, must 404 not leak)", client.get(f"/api/v1/trades/{a['trade_id']}"), 404)

        print("\n=== GET /realized-gains/trade/{sell_trade_id} ===")
        as_user(USER_A)
        r = client.get(f"/api/v1/realized-gains/trade/{a['sell_trade_id']}")
        print(f"  User A -> own gain: HTTP {r.status_code}, {len(r.json())} row(s)")
        results.append(r.status_code == 200 and len(r.json()) > 0)
        r = client.get(f"/api/v1/realized-gains/trade/{b['sell_trade_id']}")
        print(f"  User A -> User B's gain: HTTP {r.status_code}, {len(r.json())} row(s) (expect 0, not another user's data)")
        results.append(r.status_code == 200 and len(r.json()) == 0)
        as_user(b["user_id"])
        r = client.get(f"/api/v1/realized-gains/trade/{b['sell_trade_id']}")
        print(f"  User B -> own gain: HTTP {r.status_code}, {len(r.json())} row(s)")
        results.append(r.status_code == 200 and len(r.json()) > 0)
        r = client.get(f"/api/v1/realized-gains/trade/{a['sell_trade_id']}")
        print(f"  User B -> User A's gain: HTTP {r.status_code}, {len(r.json())} row(s) (expect 0)")
        results.append(r.status_code == 200 and len(r.json()) == 0)

        print("\n=== Regression: no auth override -> still 401 (unchanged by this fix) ===")
        app.dependency_overrides.clear()
        r = client.get(f"/api/v1/holdings/{a['lot_id']}")
        print(f"  No token -> HTTP {r.status_code}")
        results.append(r.status_code == 401)
    finally:
        app.dependency_overrides.clear()
        cleanup_user_b(b["user_id"])

    print(f"\n{'=' * 60}")
    print(f"{sum(results)}/{len(results)} checks passed")
    return all(results)


if __name__ == "__main__":
    ok = run()
    print("RESULT:", "ALL PASS — ownership isolation verified against real data" if ok else "FAILURES FOUND")
    sys.exit(0 if ok else 1)
