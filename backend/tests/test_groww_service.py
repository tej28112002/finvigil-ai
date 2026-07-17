"""
Phase 16 (BYOK) -- GrowwService.

Unlike Zerodha/Upstox (OAuth redirect), Groww uses a TOTP-based token flow:
  api_key (Bearer) + live TOTP code -> POST /v1/token/api/access -> token.
No login URL or callback endpoint exists; refresh_access_token is called at
the start of every sync. Tests follow the same fake-first, no-DB pattern as
test_upstox_service.py.
"""
from datetime import date
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import requests

from app.services.groww_service import GrowwService
from tests.fakes import (
    FakeBrokerConnection,
    FakeBrokerConnectionRepository,
    FakeVaultRepository,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


class FakeInstrumentRepository:
    """Returns a fresh instrument stub on get_or_create."""
    def get_or_create(self, symbol, instrument_type, name, isin):
        return SimpleNamespace(id=uuid4(), symbol=symbol, instrument_type=instrument_type)


class FakeTradeService:
    def __init__(self):
        self.calls: list[dict] = []

    def process_trade(self, **kwargs):
        self.calls.append({"type": "equity", **kwargs})

    def process_fno_buy_trade(self, **kwargs):
        self.calls.append({"type": "fno_buy", **kwargs})

    def process_fno_sell_trade(self, **kwargs):
        self.calls.append({"type": "fno_sell", **kwargs})


def make_service(repo=None, vault=None, trade_service=None, instrument_repo=None):
    return GrowwService(
        broker_connection_repository=repo or FakeBrokerConnectionRepository(),
        vault_repository=vault or FakeVaultRepository(),
        trade_service=trade_service,
        instrument_repository=instrument_repo,
    )


def make_groww_order(
    *,
    order_id="ORD001",
    symbol="RELIANCE",
    segment="CASH",
    status="EXECUTED",
    trade_date=None,
    txn_type="buy",
    qty=10,
    fill_price="2500.00",
    exchange_time=None,
):
    today = date.today().isoformat()
    return {
        "groww_order_id": order_id,
        "trading_symbol": symbol,
        "_segment": segment,
        "order_status": status,
        "trade_date": trade_date or today,
        "transaction_type": txn_type,
        "filled_quantity": qty,
        "quantity": qty,
        "average_fill_price": fill_price,
        "exchange_time": exchange_time or f"{today}T09:15:00",
    }


# ---------------------------------------------------------------------------
# refresh_access_token -- missing credentials
# ---------------------------------------------------------------------------

def test_refresh_requires_api_key():
    service = make_service()
    with pytest.raises(ValueError, match="No Groww credentials"):
        service.refresh_access_token(uuid4())


def test_refresh_requires_totp_secret_not_just_api_key():
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    repo.create_connection(user_id=user_id, broker_name="groww", api_key="my-api-key")
    # totp_secret_kms_id is None
    service = make_service(repo=repo)
    with pytest.raises(ValueError, match="No Groww credentials"):
        service.refresh_access_token(user_id)


# ---------------------------------------------------------------------------
# refresh_access_token -- happy path (new token, no prior access_token_kms_id)
# ---------------------------------------------------------------------------

def test_refresh_generates_totp_and_stores_token(monkeypatch):
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()

    totp_secret_id = vault.create_secret("BASE32SECRET", name="totp")
    conn = repo.create_connection(user_id=user_id, broker_name="groww", api_key="api-k")
    repo.update_totp_secret_kms_id(conn, str(totp_secret_id))

    service = make_service(repo=repo, vault=vault)

    captured_post = {}
    totp_codes_generated = []

    import pyotp

    original_totp_class = pyotp.TOTP

    class FakeTOTP:
        def __init__(self, secret):
            self._secret = secret
        def now(self):
            code = "123456"
            totp_codes_generated.append(code)
            return code

    monkeypatch.setattr(pyotp, "TOTP", FakeTOTP)

    def fake_post(url, json=None, headers=None, timeout=None):
        captured_post["url"] = url
        captured_post["json"] = json
        captured_post["auth_header"] = headers.get("Authorization")
        return FakeResponse({"token": "fresh-access-token"})

    monkeypatch.setattr(requests, "post", fake_post)

    token = service.refresh_access_token(user_id)

    assert token == "fresh-access-token"
    assert captured_post["auth_header"] == "Bearer api-k"
    assert captured_post["json"]["key_type"] == "totp"
    assert captured_post["json"]["totp"] == "123456"
    assert totp_codes_generated == ["123456"]

    # Token stored in Vault and connection updated
    assert conn.access_token_kms_id is not None
    stored = vault.get_secret(UUID(conn.access_token_kms_id))
    assert stored == "fresh-access-token"
    assert conn.status == "active"


# ---------------------------------------------------------------------------
# refresh_access_token -- update path (access_token_kms_id already exists)
# ---------------------------------------------------------------------------

def test_refresh_updates_existing_vault_entry(monkeypatch):
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()

    totp_secret_id = vault.create_secret("BASE32SECRET", name="totp")
    old_token_id = vault.create_secret("old-token", name="old")
    conn = repo.create_connection(user_id=user_id, broker_name="groww", api_key="k")
    repo.update_totp_secret_kms_id(conn, str(totp_secret_id))
    repo.update_access_token_kms_id(conn, str(old_token_id))

    service = make_service(repo=repo, vault=vault)

    import pyotp

    class FakeTOTP:
        def __init__(self, secret): pass
        def now(self): return "654321"

    monkeypatch.setattr(pyotp, "TOTP", FakeTOTP)
    monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse({"token": "refreshed-token"}))

    token = service.refresh_access_token(user_id)

    assert token == "refreshed-token"
    # Same KMS id (update, not create)
    assert conn.access_token_kms_id == str(old_token_id)
    assert vault.get_secret(old_token_id) == "refreshed-token"


# ---------------------------------------------------------------------------
# refresh_access_token -- HTTP error wrapping
# ---------------------------------------------------------------------------

def test_refresh_wraps_http_failure(monkeypatch):
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()

    totp_secret_id = vault.create_secret("SECRET", name="s")
    conn = repo.create_connection(user_id=user_id, broker_name="groww", api_key="k")
    repo.update_totp_secret_kms_id(conn, str(totp_secret_id))

    service = make_service(repo=repo, vault=vault)

    import pyotp

    class FakeTOTP:
        def __init__(self, s): pass
        def now(self): return "000000"

    monkeypatch.setattr(pyotp, "TOTP", FakeTOTP)
    monkeypatch.setattr(
        requests, "post",
        lambda *a, **kw: FakeResponse({"error": "invalid_key"}, status_code=401),
    )

    with pytest.raises(ValueError, match="Failed to generate Groww access token"):
        service.refresh_access_token(user_id)


# ---------------------------------------------------------------------------
# sync_today_trades -- date and status filtering
# ---------------------------------------------------------------------------

def _make_syncing_service(monkeypatch, orders_by_segment, *, today_override=None):
    """
    Helper: creates a GrowwService wired with fake credentials, mocks
    requests.post (token refresh) and requests.get (order list), and returns
    (service, user_id, broker_connection_id, trade_service).
    """
    import pyotp

    user_id = uuid4()
    broker_connection_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()

    totp_id = vault.create_secret("SECRET", name="t")
    conn = repo.create_connection(user_id=user_id, broker_name="groww", api_key="k")
    repo.update_totp_secret_kms_id(conn, str(totp_id))

    class FakeTOTP:
        def __init__(self, s): pass
        def now(self): return "000000"

    monkeypatch.setattr(pyotp, "TOTP", FakeTOTP)
    monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse({"token": "tok"}))

    def fake_get(url, params=None, headers=None, timeout=None):
        segment = params.get("segment", "CASH")
        orders = orders_by_segment.get(segment, [])
        return FakeResponse({"payload": {"order_list": orders}})

    monkeypatch.setattr(requests, "get", fake_get)

    trade_svc = FakeTradeService()
    service = GrowwService(
        broker_connection_repository=repo,
        vault_repository=vault,
        trade_service=trade_svc,
        instrument_repository=FakeInstrumentRepository(),
    )
    return service, user_id, broker_connection_id, trade_svc


def test_sync_skips_non_executed_orders(monkeypatch):
    pending_order = make_groww_order(status="PENDING")
    service, user_id, conn_id, trade_svc = _make_syncing_service(
        monkeypatch, {"CASH": [pending_order], "FNO": []}
    )
    result = service.sync_today_trades(user_id=user_id, broker_connection_id=conn_id)
    assert result.imported == 0
    assert trade_svc.calls == []


def test_sync_skips_old_trade_dates(monkeypatch):
    old_order = make_groww_order(trade_date="2000-01-01", status="EXECUTED")
    service, user_id, conn_id, trade_svc = _make_syncing_service(
        monkeypatch, {"CASH": [old_order], "FNO": []}
    )
    result = service.sync_today_trades(user_id=user_id, broker_connection_id=conn_id)
    assert result.imported == 0
    assert trade_svc.calls == []


def test_sync_imports_todays_executed_equity_order(monkeypatch):
    order = make_groww_order(
        order_id="EQ1", symbol="TCS", segment="CASH",
        status="EXECUTED", txn_type="buy", qty=5, fill_price="3800.00",
    )
    service, user_id, conn_id, trade_svc = _make_syncing_service(
        monkeypatch, {"CASH": [order], "FNO": []}
    )
    result = service.sync_today_trades(user_id=user_id, broker_connection_id=conn_id)
    assert result.imported == 1
    assert result.errors == []
    assert len(trade_svc.calls) == 1
    call = trade_svc.calls[0]
    assert call["type"] == "equity"
    assert call["trade_type"] == "buy"


def test_sync_imports_todays_executed_fno_order(monkeypatch):
    order = make_groww_order(
        order_id="FO1", symbol="NIFTY25JULFUT", segment="FNO",
        status="EXECUTED", txn_type="sell", qty=50, fill_price="24500.00",
    )
    service, user_id, conn_id, trade_svc = _make_syncing_service(
        monkeypatch, {"CASH": [], "FNO": [order]}
    )
    result = service.sync_today_trades(user_id=user_id, broker_connection_id=conn_id)
    assert result.imported == 1
    assert len(trade_svc.calls) == 1
    call = trade_svc.calls[0]
    assert call["type"] == "fno_sell"


def test_sync_handles_both_segments(monkeypatch):
    cash_order = make_groww_order(order_id="C1", symbol="INFY", segment="CASH")
    fno_order = make_groww_order(
        order_id="F1", symbol="BANKNIFTY25JULFUT", segment="FNO", txn_type="buy"
    )
    service, user_id, conn_id, trade_svc = _make_syncing_service(
        monkeypatch, {"CASH": [cash_order], "FNO": [fno_order]}
    )
    result = service.sync_today_trades(user_id=user_id, broker_connection_id=conn_id)
    assert result.imported == 2
    types = {c["type"] for c in trade_svc.calls}
    assert types == {"equity", "fno_buy"}


def test_sync_deduplicates_on_idempotency_hash(monkeypatch):
    order = make_groww_order(order_id="DUP1", symbol="SBIN")

    user_id = uuid4()
    conn_id = uuid4()
    import pyotp

    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()
    totp_id = vault.create_secret("SECRET", name="t")
    conn = repo.create_connection(user_id=user_id, broker_name="groww", api_key="k")
    repo.update_totp_secret_kms_id(conn, str(totp_id))

    class FakeTOTP:
        def __init__(self, s): pass
        def now(self): return "000000"

    monkeypatch.setattr(pyotp, "TOTP", FakeTOTP)
    monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse({"token": "tok"}))
    def fake_get_dedup(url, params=None, headers=None, timeout=None):
        segment = (params or {}).get("segment", "CASH")
        return FakeResponse({"payload": {"order_list": [order] if segment == "CASH" else []}})

    monkeypatch.setattr(requests, "get", fake_get_dedup)

    call_count = 0

    class DuplicateTradeService:
        def process_trade(self, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("duplicate key value violates unique constraint on idempotency_hash")

    service = GrowwService(
        broker_connection_repository=repo,
        vault_repository=vault,
        trade_service=DuplicateTradeService(),
        instrument_repository=FakeInstrumentRepository(),
    )
    result = service.sync_today_trades(user_id=user_id, broker_connection_id=conn_id)
    # duplicate errors are counted as skipped, not errors
    assert result.skipped == 1
    assert result.errors == []
