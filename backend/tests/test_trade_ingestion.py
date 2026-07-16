"""
Trade ingestion + idempotency (Phase 15.1 continuation, priority #5) --
app.core.idempotency.generate_trade_idempotency_hash and TradeService's
buy/sell dispatch and processing correctness.
"""
import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.idempotency import generate_trade_idempotency_hash
from app.services.trade_service import TradeService


def test_idempotency_hash_is_deterministic():
    """Same inputs must always produce the same hash -- this is the whole
    point (relied on by the DB's UNIQUE(idempotency_hash) constraint to
    reject a re-imported duplicate trade). Verified independently via a
    fresh hashlib.sha256 call, not by calling the function twice and
    comparing to itself."""
    conn_id = uuid4()
    hash1 = generate_trade_idempotency_hash(conn_id, "TRADE-001")
    hash2 = generate_trade_idempotency_hash(conn_id, "TRADE-001")

    expected = hashlib.sha256(f"{conn_id}:TRADE-001".encode()).hexdigest()
    assert hash1 == hash2 == expected


def test_idempotency_hash_differs_for_different_broker_trade_id():
    conn_id = uuid4()
    assert generate_trade_idempotency_hash(conn_id, "TRADE-001") != generate_trade_idempotency_hash(conn_id, "TRADE-002")


def test_idempotency_hash_differs_across_broker_connections():
    """Same broker_trade_id but a different broker_connection_id (e.g. two
    different brokers both numbering their own trades '1') must NOT
    collide -- the ':' separator in the raw string is specifically what
    prevents this."""
    trade_id = "1"
    assert generate_trade_idempotency_hash(uuid4(), trade_id) != generate_trade_idempotency_hash(uuid4(), trade_id)


class FakeTradeRepository:
    def __init__(self):
        self.trades = []

    def create_trade(self, **kwargs):
        from types import SimpleNamespace
        trade = SimpleNamespace(id=uuid4(), **kwargs)
        self.trades.append(trade)
        return trade


class FakeHoldingServiceForTrade:
    """Records calls without touching real FIFO logic -- TradeService's own
    orchestration (does it call the right methods with the right args) is
    what's under test here, not FIFO correctness itself (covered in
    test_fifo_engine.py)."""

    def __init__(self, consumption_result=None):
        self.created_lots = []
        self.consumption_result = consumption_result or []
        self.consume_calls = []

    def create_holding_lot(self, **kwargs):
        self.created_lots.append(kwargs)

    def consume_lots_fifo(self, **kwargs):
        self.consume_calls.append(kwargs)
        return self.consumption_result


class FakeRealizedGainRepositoryForTrade:
    def __init__(self):
        self.created = []

    def create_realized_gain(self, **kwargs):
        self.created.append(kwargs)


def test_validate_trade_type_accepts_buy_and_sell_case_insensitive():
    trade_repo = FakeTradeRepository()
    service = TradeService(trade_repo, FakeHoldingServiceForTrade(), FakeRealizedGainRepositoryForTrade())
    service.validate_trade_type("buy")
    service.validate_trade_type("SELL")
    service.validate_trade_type("Buy")


def test_validate_trade_type_rejects_unknown_type():
    trade_repo = FakeTradeRepository()
    service = TradeService(trade_repo, FakeHoldingServiceForTrade(), FakeRealizedGainRepositoryForTrade())
    with pytest.raises(ValueError, match="Invalid trade type"):
        service.validate_trade_type("short")


def test_process_buy_trade_creates_trade_and_holding_lot():
    trade_repo = FakeTradeRepository()
    holding_service = FakeHoldingServiceForTrade()
    service = TradeService(trade_repo, holding_service, FakeRealizedGainRepositoryForTrade())

    service.process_trade(
        "buy", user_id=uuid4(), instrument_id=uuid4(), broker_connection_id=uuid4(),
        broker_trade_id="T1", quantity=Decimal("10"), price=Decimal("100"),
        execution_time=datetime(2025, 1, 1, tzinfo=timezone.utc), idempotency_hash="h1",
    )

    assert len(trade_repo.trades) == 1
    assert trade_repo.trades[0].trade_type == "buy"
    assert len(holding_service.created_lots) == 1
    assert holding_service.created_lots[0]["quantity"] == Decimal("10")


def test_process_sell_trade_consumes_fifo_and_records_realized_gains():
    trade_repo = FakeTradeRepository()
    consumption = [{
        "lot_id": uuid4(), "buy_date": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "buy_price": Decimal("100"), "quantity_consumed": Decimal("5"),
        "sell_price": Decimal("120"), "sell_date": datetime(2025, 2, 1, tzinfo=timezone.utc),
        "holding_days": 31, "gain_type": "STCG", "profit_loss": Decimal("100"),
    }]
    holding_service = FakeHoldingServiceForTrade(consumption_result=consumption)
    gain_repo = FakeRealizedGainRepositoryForTrade()
    service = TradeService(trade_repo, holding_service, gain_repo)

    service.process_trade(
        "sell", user_id=uuid4(), instrument_id=uuid4(), broker_connection_id=uuid4(),
        broker_trade_id="T2", quantity=Decimal("5"), price=Decimal("120"),
        execution_time=datetime(2025, 2, 1, tzinfo=timezone.utc), idempotency_hash="h2",
    )

    assert len(holding_service.consume_calls) == 1
    assert len(gain_repo.created) == 1
    assert gain_repo.created[0]["profit_loss"] == Decimal("100")
    assert gain_repo.created[0]["gain_type"] == "STCG"


def test_process_trade_rejects_unknown_type():
    service = TradeService(FakeTradeRepository(), FakeHoldingServiceForTrade(), FakeRealizedGainRepositoryForTrade())
    with pytest.raises(ValueError):
        service.process_trade("short", user_id=uuid4())


def test_duplicate_broker_trade_id_rejected_by_real_db(db_test_user, db_session):
    """
    Real-DB integration test: the actual UNIQUE(idempotency_hash)
    constraint that CSV import / Zerodha sync rely on to silently skip a
    re-imported trade -- verified against a real IntegrityError, not
    assumed from reading the schema.
    """
    import uuid as uuid_module
    from sqlalchemy import text
    from tests.conftest import RELIANCE_INSTRUMENT_ID

    user_id = uuid_module.UUID(db_test_user["user_id"])
    broker_id = uuid_module.UUID(db_test_user["broker_connection_id"])
    instrument_id = uuid_module.UUID(RELIANCE_INSTRUMENT_ID)
    same_hash = generate_trade_idempotency_hash(broker_id, "DUPLICATE-TEST-1")

    db_session.execute(
        text(
            "INSERT INTO trades (user_id, broker_connection_id, instrument_id, broker_trade_id, "
            "trade_type, quantity, price, execution_time, idempotency_hash) "
            "VALUES (:uid, :bcid, :iid, 'DUPLICATE-TEST-1', 'buy', 10, 100, now(), :hash)"
        ),
        {"uid": user_id, "bcid": broker_id, "iid": instrument_id, "hash": same_hash},
    )
    db_session.flush()

    with pytest.raises(Exception, match="(?i)duplicate|unique"):
        db_session.execute(
            text(
                "INSERT INTO trades (user_id, broker_connection_id, instrument_id, broker_trade_id, "
                "trade_type, quantity, price, execution_time, idempotency_hash) "
                "VALUES (:uid, :bcid, :iid, 'DUPLICATE-TEST-1-AGAIN', 'buy', 10, 100, now(), :hash)"
            ),
            {"uid": user_id, "bcid": broker_id, "iid": instrument_id, "hash": same_hash},
        )
        db_session.flush()
