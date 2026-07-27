"""
FIX 4 -- broker sync was showing Rs 0.00 holdings / 0 trades for correctly
connected accounts. Root cause: sync_today_trades() only ever called Kite's
/trades (Zerodha) or /order/trades/get-trades-for-day (Upstox) endpoints,
which return orders placed TODAY -- an account with pre-existing holdings
bought before the app was ever connected legitimately gets nothing there.

These tests cover the new sync_holdings()/sync_broker() methods, which
fetch the user's actual portfolio holdings and upsert them as HoldingLots.
No real Zerodha/Upstox API calls -- kite.holdings() and requests.get are
monkeypatched.
"""
from decimal import Decimal
from uuid import uuid4

import pytest
import requests
from kiteconnect import KiteConnect
from kiteconnect.exceptions import TokenException

from app.services.holding_service import HoldingLotService
from app.services.trade_service import TradeService
from app.services.upstox_service import UpstoxService
from app.services.zerodha_service import ZerodhaService
from tests.fakes import (
    FakeBrokerConnectionRepository,
    FakeHoldingLotRepository,
    FakeInstrumentRepository,
    FakeRealizedGainRepository,
    FakeTradeRepository,
    FakeVaultRepository,
)


def _wired_service(cls, broker_name: str, api_key="my-key"):
    """Builds a Zerodha/UpstoxService with a real TradeService/
    HoldingLotService against fakes, plus a connected+tokened broker
    connection -- same "real service, fake repos" pattern as
    test_trade_upload.py."""
    user_id = uuid4()
    broker_repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()
    token_secret_id = vault.create_secret("valid-access-token", name="x")
    conn = broker_repo.create_connection(
        user_id=user_id, broker_name=broker_name, api_key=api_key,
    )
    broker_repo.update_access_token_kms_id(conn, str(token_secret_id))

    trade_repo = FakeTradeRepository([])
    holding_repo = FakeHoldingLotRepository([])
    trade_service = TradeService(
        trade_repository=trade_repo,
        holding_service=HoldingLotService(holding_repository=holding_repo),
        realized_gain_repository=FakeRealizedGainRepository([]),
    )
    service = cls(
        broker_connection_repository=broker_repo,
        vault_repository=vault,
        trade_service=trade_service,
        instrument_repository=FakeInstrumentRepository(),
        holding_lot_repository=holding_repo,
    )
    return service, user_id, holding_repo


# --- Zerodha: sync_holdings creates lots from /portfolio/holdings ---

def test_zerodha_sync_holdings_creates_lot_from_broker_holdings(monkeypatch):
    service, user_id, holding_repo = _wired_service(ZerodhaService, "zerodha")

    def fake_holdings(self):
        return [
            {"tradingsymbol": "RELIANCE", "isin": "INE002A01018", "quantity": 10, "average_price": 2500.0},
            # Zero-quantity holding (fully sold on the broker side) is skipped.
            {"tradingsymbol": "TCS", "isin": "INE467B01029", "quantity": 0, "average_price": 3800.0},
        ]

    monkeypatch.setattr(KiteConnect, "holdings", fake_holdings)

    result = service.sync_holdings(user_id=user_id, broker_connection_id=uuid4())

    assert result["success"] is True
    assert result["holdings_synced"] == 1
    assert len(holding_repo.lots) == 1
    assert holding_repo.lots[0].quantity_remaining == Decimal("10")


def test_zerodha_sync_holdings_resync_updates_existing_lot_quantity(monkeypatch):
    service, user_id, holding_repo = _wired_service(ZerodhaService, "zerodha")
    broker_connection_id = uuid4()

    call_count = {"n": 0}

    def fake_holdings(self):
        call_count["n"] += 1
        qty = 10 if call_count["n"] == 1 else 15
        return [{"tradingsymbol": "RELIANCE", "isin": "INE002A01018", "quantity": qty, "average_price": 2500.0}]

    monkeypatch.setattr(KiteConnect, "holdings", fake_holdings)

    first = service.sync_holdings(user_id=user_id, broker_connection_id=broker_connection_id)
    second = service.sync_holdings(user_id=user_id, broker_connection_id=broker_connection_id)

    assert first["holdings_synced"] == 1
    assert second["holdings_synced"] == 1
    # Same lot updated in place, not a second lot created.
    assert len(holding_repo.lots) == 1
    assert holding_repo.lots[0].quantity_remaining == Decimal("15")


def test_zerodha_sync_holdings_returns_token_expired_error_code(monkeypatch):
    service, user_id, _ = _wired_service(ZerodhaService, "zerodha")

    def fake_holdings(self):
        raise TokenException("Incorrect `api_key` or `access_token`.")

    monkeypatch.setattr(KiteConnect, "holdings", fake_holdings)

    result = service.sync_holdings(user_id=user_id, broker_connection_id=uuid4())

    assert result["success"] is False
    assert result["error_code"] == "TOKEN_EXPIRED"


def test_zerodha_sync_holdings_returns_missing_credentials_when_not_connected():
    service, _, _ = _wired_service(ZerodhaService, "zerodha")

    result = service.sync_holdings(user_id=uuid4(), broker_connection_id=uuid4())

    assert result["success"] is False
    assert result["error_code"] == "MISSING_CREDENTIALS"


# --- Upstox: sync_holdings creates lots from /portfolio/long-term-holdings ---

class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data


def test_upstox_sync_holdings_creates_lot_from_broker_holdings(monkeypatch):
    service, user_id, holding_repo = _wired_service(UpstoxService, "upstox")

    def fake_get(url, headers=None, timeout=None):
        return FakeResponse({
            "data": [
                {"trading_symbol": "INFY", "isin": "INE009A01021", "quantity": 5, "average_price": 1500.0},
            ]
        })

    monkeypatch.setattr(requests, "get", fake_get)

    result = service.sync_holdings(user_id=user_id, broker_connection_id=uuid4())

    assert result["success"] is True
    assert result["holdings_synced"] == 1
    assert len(holding_repo.lots) == 1
    assert holding_repo.lots[0].quantity_remaining == Decimal("5")


def test_upstox_sync_holdings_returns_token_expired_error_code(monkeypatch):
    service, user_id, _ = _wired_service(UpstoxService, "upstox")

    def fake_get(url, headers=None, timeout=None):
        return FakeResponse({}, status_code=401)

    monkeypatch.setattr(requests, "get", fake_get)

    result = service.sync_holdings(user_id=user_id, broker_connection_id=uuid4())

    assert result["success"] is False
    assert result["error_code"] == "TOKEN_EXPIRED"


def test_upstox_sync_holdings_returns_timeout_error_code(monkeypatch):
    service, user_id, _ = _wired_service(UpstoxService, "upstox")

    def fake_get(url, headers=None, timeout=None):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(requests, "get", fake_get)

    result = service.sync_holdings(user_id=user_id, broker_connection_id=uuid4())

    assert result["success"] is False
    assert result["error_code"] == "TIMEOUT"
