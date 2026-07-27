"""
Regression test for FIX 3's savepoint pattern in csv_import_service.py --
a real IntegrityError on one row must not poison the rest of the batch.
No DB, no real file parsing -- CsvParserService is stubbed to return fixed
rows; TradeService is wired against tests/fakes.py fakes, the same "real
service, fake repos" pattern used across this project (see
test_trade_upload.py, test_broker_sync.py).
"""
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.services.csv_import_service import CsvImportService
from app.services.holding_service import HoldingLotService
from app.services.trade_service import TradeService
from tests.fakes import (
    FakeHoldingLotRepository,
    FakeInstrumentRepository,
    FakeRealizedGainRepository,
    FakeTradeRepository,
)


class FakeCsvParserService:
    def __init__(self, rows):
        self.rows = rows

    def parse_tradebook(self, file_content, filename):
        return self.rows


def _make_row(trade_id: str, symbol: str) -> dict:
    return {
        "segment": "EQ",
        "symbol": symbol,
        "isin": None,
        "order_execution_time": datetime(2025, 1, 10, 9, 15).isoformat(),
        "trade_date": "2025-01-10",
        "trade_id": trade_id,
        "trade_type": "buy",
        "quantity": 10,
        "price": Decimal("2500.00"),
    }


def _make_service(rows):
    trade_repo = FakeTradeRepository([])
    holding_repo = FakeHoldingLotRepository([])
    trade_service = TradeService(
        trade_repository=trade_repo,
        holding_service=HoldingLotService(holding_repository=holding_repo),
        realized_gain_repository=FakeRealizedGainRepository([]),
    )
    return CsvImportService(
        csv_parser_service=FakeCsvParserService(rows),
        trade_service=trade_service,
        instrument_repository=FakeInstrumentRepository(),
    )


def test_import_tradebook_processes_all_valid_rows():
    rows = [_make_row("T1", "RELIANCE"), _make_row("T2", "TCS")]
    service = _make_service(rows)

    result = service.import_tradebook(
        file_content=b"irrelevant, parser is stubbed",
        filename="tradebook.csv",
        user_id=uuid4(),
        broker_connection_id=uuid4(),
    )

    assert result.imported == 2
    assert result.skipped == 0
    assert result.errors == []


def test_import_continues_after_integrity_error_on_one_row(monkeypatch):
    rows = [
        _make_row("T1", "RELIANCE"),
        _make_row("T2", "TCS"),
        _make_row("T3", "SBIN"),
    ]
    service = _make_service(rows)

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
    result = service.import_tradebook(
        file_content=b"irrelevant, parser is stubbed",
        filename="tradebook.csv",
        user_id=uuid4(),
        broker_connection_id=uuid4(),
    )

    assert call_count["n"] == 3
    assert result.imported == 2
    assert result.skipped == 1
    assert result.errors == []
