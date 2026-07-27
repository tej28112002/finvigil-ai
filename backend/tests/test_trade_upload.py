"""
Unit tests for trade_upload_service.py. No DB, no network.

Tests 1-2 exercise parse_trade_rows() (pure pandas + validation logic)
directly. Test 3 wires the real TradeService/InstrumentService/
HoldingLotService against fakes from tests/fakes.py (same "real service,
fake repos" pattern used across this project) to verify duplicate
detection actually round-trips through the full pipeline.
"""
from uuid import uuid4

import pandas as pd
from sqlalchemy.exc import IntegrityError

from app.services.holding_service import HoldingLotService
from app.services.instrument_service import InstrumentService
from app.services.trade_service import TradeService
from app.services.trade_upload_service import TradeUploadService, parse_trade_rows
from tests.fakes import (
    FakeBrokerConnectionRepository,
    FakeHoldingLotRepository,
    FakeInstrumentRepository,
    FakeRealizedGainRepository,
    FakeTradeRepository,
)


def test_parse_trade_rows_detects_buy_and_sell():
    df = pd.DataFrame({
        "symbol": ["RELIANCE", "TCS", "RELIANCE"],
        "trade_type": ["BUY", "buy", "SELL"],
        "quantity": [10, 5, 3],
        "price": [2500.0, 3800.0, 2600.0],
        "date": ["2025-01-10", "2025-02-11", "2025-03-12"],
    })

    valid_rows, errors, failed = parse_trade_rows(df)

    assert failed == 0
    assert len(valid_rows) == 3
    assert [r["trade_type"] for r in valid_rows] == ["buy", "buy", "sell"]
    assert [r["symbol"] for r in valid_rows] == ["RELIANCE", "TCS", "RELIANCE"]


def test_parse_trade_rows_skips_invalid_rows():
    df = pd.DataFrame({
        "symbol": ["RELIANCE", ""],
        "trade_type": ["BUY", "BUY"],
        "quantity": [10, 5],
        "price": [2500.0, 100.0],
        "date": ["2025-01-10", "2025-01-11"],
    })

    valid_rows, errors, failed = parse_trade_rows(df)

    assert len(valid_rows) == 1
    assert failed == 1
    assert len(errors) == 1


def _upload_service():
    trade_repo = FakeTradeRepository([])
    holding_repo = FakeHoldingLotRepository([])
    realized_repo = FakeRealizedGainRepository([])
    trade_service = TradeService(
        trade_repository=trade_repo,
        holding_service=HoldingLotService(holding_repository=holding_repo),
        realized_gain_repository=realized_repo,
    )
    instrument_service = InstrumentService(instrument_repository=FakeInstrumentRepository())
    broker_repo = FakeBrokerConnectionRepository([])

    return TradeUploadService(
        trade_repository=trade_repo,
        instrument_service=instrument_service,
        broker_connection_repository=broker_repo,
        trade_service=trade_service,
    )


def _single_row_csv() -> bytes:
    df = pd.DataFrame({
        "symbol": ["RELIANCE"],
        "trade_type": ["BUY"],
        "quantity": [10],
        "price": [2500.0],
        "date": ["2025-01-10"],
    })
    return df.to_csv(index=False).encode()


def test_duplicate_upload_is_skipped_on_second_submission():
    service = _upload_service()
    user_id = uuid4()
    csv_bytes = _single_row_csv()

    first = service.process_upload(csv_bytes, "tradebook.csv", user_id)
    assert first["trades_processed"] == 1
    assert first["trades_skipped"] == 0

    second = service.process_upload(csv_bytes, "tradebook.csv", user_id)
    assert second["trades_processed"] == 0
    assert second["trades_skipped"] == 1


def test_upload_continues_after_integrity_error_on_one_row(monkeypatch):
    """FIX 3: a real IntegrityError on one row (e.g. a race between two
    concurrent uploads) must not poison the rest of the batch -- the
    savepoint around each row's write should isolate it."""
    service = _upload_service()
    user_id = uuid4()

    df = pd.DataFrame({
        "symbol": ["RELIANCE", "TCS", "SBIN"],
        "trade_type": ["BUY", "BUY", "BUY"],
        "quantity": [10, 5, 8],
        "price": [2500.0, 3800.0, 600.0],
        "date": ["2025-01-10", "2025-01-11", "2025-01-12"],
    })
    csv_bytes = df.to_csv(index=False).encode()

    call_count = {"n": 0}
    original_process_trade = TradeService.process_trade

    def flaky_process_trade(self, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise IntegrityError(
                "INSERT INTO trades ...", {},
                Exception(
                    "duplicate key value violates unique constraint "
                    "\"trades_idempotency_hash_key\""
                ),
            )
        return original_process_trade(self, **kwargs)

    monkeypatch.setattr(TradeService, "process_trade", flaky_process_trade)

    # Must not raise -- the whole point of the savepoint fix.
    result = service.process_upload(csv_bytes, "tradebook.csv", user_id)

    assert call_count["n"] == 3
    assert result["trades_processed"] == 2
    assert result["trades_skipped"] == 1
    assert result["trades_failed"] == 0
