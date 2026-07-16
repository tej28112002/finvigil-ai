"""
FIFO cost-basis engine (HoldingLotService.consume_lots_fifo) — highest
money-risk item per Phase 15.1 scope: wrong lot consumption order or wrong
holding-period classification directly misstates real STCG/LTCG figures.

Unit tests use FakeHoldingLotRepository (tests/fakes.py) — no DB, no
network. Expected values below are hand-computed independently from the
inputs (qty * price arithmetic, calendar day differences), not derived by
reading what the code currently returns.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

import uuid

from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.trade_repository import TradeRepository
from app.services.holding_service import HoldingLotService
from tests.conftest import RELIANCE_INSTRUMENT_ID
from tests.fakes import FakeHoldingLotRepository, FakeLot

DAY1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
DAY2 = datetime(2024, 2, 1, tzinfo=timezone.utc)


def make_service(lots):
    repo = FakeHoldingLotRepository(lots)
    return HoldingLotService(holding_repository=repo), repo


def test_fifo_consumes_oldest_lot_first():
    """Two lots, sell less than the oldest lot's full quantity -> only the
    oldest (lowest buy_date) lot is touched, exactly as FIFO requires."""
    older = FakeLot(quantity_remaining=Decimal("10"), buy_price=Decimal("100"), buy_date=DAY1)
    newer = FakeLot(quantity_remaining=Decimal("10"), buy_price=Decimal("200"), buy_date=DAY2)
    service, repo = make_service([older, newer])

    result = service.consume_lots_fifo(
        user_id=None, instrument_id=None,
        sell_quantity=Decimal("5"), sell_price=Decimal("150"),
        sell_date=DAY1 + timedelta(days=10),
    )

    assert len(result) == 1
    assert result[0]["lot_id"] == older.id
    assert result[0]["quantity_consumed"] == Decimal("5")
    # (150 - 100) * 5 = 250, hand-computed independently of the code
    assert result[0]["profit_loss"] == Decimal("250")
    assert older.quantity_remaining == Decimal("5")
    assert older.status == "partial"
    # Newer lot must be completely untouched -- FIFO didn't need to dip into it.
    assert newer.quantity_remaining == Decimal("10")
    assert len(repo.update_calls) == 1


def test_fifo_exact_quantity_match():
    """Selling exactly a lot's remaining quantity closes it fully, not
    'partial' -- an off-by-one here would misreport open/closed status on
    every future dashboard/tax read for this lot."""
    lot = FakeLot(quantity_remaining=Decimal("10"), buy_price=Decimal("50"), buy_date=DAY1)
    service, _ = make_service([lot])

    result = service.consume_lots_fifo(
        user_id=None, instrument_id=None,
        sell_quantity=Decimal("10"), sell_price=Decimal("60"),
        sell_date=DAY1 + timedelta(days=5),
    )

    assert len(result) == 1
    assert result[0]["quantity_consumed"] == Decimal("10")
    assert lot.quantity_remaining == Decimal("0")
    assert lot.status == "closed"


def test_fifo_spans_multiple_lots():
    """Sell quantity exceeds the oldest lot -> first lot fully consumed
    (closed), remainder pulled from the next-oldest lot (partial). Verifies
    both the split point and that quantities sum back to the sell amount."""
    lot1 = FakeLot(quantity_remaining=Decimal("5"), buy_price=Decimal("100"), buy_date=DAY1)
    lot2 = FakeLot(quantity_remaining=Decimal("10"), buy_price=Decimal("200"), buy_date=DAY2)
    service, _ = make_service([lot1, lot2])

    result = service.consume_lots_fifo(
        user_id=None, instrument_id=None,
        sell_quantity=Decimal("12"), sell_price=Decimal("250"),
        sell_date=DAY2 + timedelta(days=1),
    )

    assert len(result) == 2
    assert result[0]["lot_id"] == lot1.id
    assert result[0]["quantity_consumed"] == Decimal("5")
    assert result[0]["profit_loss"] == Decimal("750")  # (250-100)*5
    assert result[1]["lot_id"] == lot2.id
    assert result[1]["quantity_consumed"] == Decimal("7")
    assert result[1]["profit_loss"] == Decimal("350")  # (250-200)*7

    assert lot1.status == "closed" and lot1.quantity_remaining == Decimal("0")
    assert lot2.status == "partial" and lot2.quantity_remaining == Decimal("3")
    total_consumed = sum(r["quantity_consumed"] for r in result)
    assert total_consumed == Decimal("12")


def test_fifo_insufficient_shares_raises_and_touches_nothing():
    """Selling more than total available must raise before mutating any
    lot -- a partial FIFO consumption on a rejected sell would silently
    corrupt cost basis for a trade that (from the user's point of view)
    never happened."""
    lot = FakeLot(quantity_remaining=Decimal("5"), buy_price=Decimal("100"), buy_date=DAY1)
    service, repo = make_service([lot])

    with pytest.raises(ValueError, match="Insufficient shares"):
        service.consume_lots_fifo(
            user_id=None, instrument_id=None,
            sell_quantity=Decimal("10"), sell_price=Decimal("100"),
            sell_date=DAY1 + timedelta(days=1),
        )

    assert lot.quantity_remaining == Decimal("5")
    assert repo.update_calls == []


def test_fifo_no_open_lots_raises():
    service, _ = make_service([])
    with pytest.raises(ValueError, match="No open lots"):
        service.consume_lots_fifo(
            user_id=None, instrument_id=None,
            sell_quantity=Decimal("1"), sell_price=Decimal("100"),
            sell_date=DAY1,
        )


class TestHoldingPeriodBoundary:
    """
    LTCG classification boundary, tested at the exact three points the user
    asked for. holding_service.py uses `holding_days > 365` (strictly
    greater), so day 365 itself is still STCG -- only day 366+ is LTCG.

    Caveat documented here, not silently assumed: Indian tax law defines
    LTCG for listed equity as a holding period exceeding 12 CALENDAR
    months, not a fixed day count -- a true 12-month span is 365 or 366
    days depending on which months/leap-years it crosses. A fixed
    365-day cutover is a reasonable, common approximation, but is not
    byte-for-byte identical to calendar-month arithmetic in every case.
    These tests confirm the fixed-365 rule is applied exactly as
    documented/consistently, not that it's a legally perfect substitute
    for calendar-month math -- that's a separate, larger question outside
    this test's scope.
    """

    def _classify(self, days_held: int) -> str:
        lot = FakeLot(
            quantity_remaining=Decimal("1"),
            buy_price=Decimal("100"),
            buy_date=DAY1,
        )
        service, _ = make_service([lot])
        result = service.consume_lots_fifo(
            user_id=None, instrument_id=None,
            sell_quantity=Decimal("1"), sell_price=Decimal("110"),
            sell_date=DAY1 + timedelta(days=days_held),
        )
        assert result[0]["holding_days"] == days_held
        return result[0]["gain_type"]

    def test_364_days_is_stcg(self):
        assert self._classify(364) == "STCG"

    def test_365_days_is_still_stcg(self):
        assert self._classify(365) == "STCG"

    def test_366_days_is_ltcg(self):
        assert self._classify(366) == "LTCG"


def test_fifo_decimal_precision_no_float_rounding():
    """Fractional prices must stay exact via Decimal -- this would silently
    lose precision if the engine ever used float arithmetic."""
    lot = FakeLot(quantity_remaining=Decimal("3"), buy_price=Decimal("99.995"), buy_date=DAY1)
    service, _ = make_service([lot])

    result = service.consume_lots_fifo(
        user_id=None, instrument_id=None,
        sell_quantity=Decimal("3"), sell_price=Decimal("100.005"),
        sell_date=DAY1 + timedelta(days=1),
    )

    # (100.005 - 99.995) * 3 = 0.01 * 3 = 0.03 exactly
    assert result[0]["profit_loss"] == Decimal("0.03")


def test_fifo_against_real_db(db_test_user, db_session):
    """
    Integration test: same FIFO logic, but through the real
    HoldingLotRepository against the real Supabase DB, using a dedicated
    disposable user (never the shared documented test user) that the
    db_test_user fixture cleans up automatically afterward. Proves the ORM
    mapping and real Postgres round-trip agree with the hand-computed
    expected value, not just the fake repository.
    """
    user_id = uuid.UUID(db_test_user["user_id"])
    broker_id = uuid.UUID(db_test_user["broker_connection_id"])
    instrument_id = uuid.UUID(RELIANCE_INSTRUMENT_ID)

    repo = HoldingLotRepository(db_session)
    service = HoldingLotService(holding_repository=repo)
    trade_repo = TradeRepository(db_session)

    # holding_lots.source_trade_id has a real FK to trades.id -- a lot can't
    # exist without a backing trade row, so create those first (mirrors
    # TradeService.process_buy_trade's real order of operations).
    trade1 = trade_repo.create_trade(
        user_id=user_id, broker_connection_id=broker_id, instrument_id=instrument_id,
        broker_trade_id="phase15-fifo-buy-1", trade_type="buy",
        quantity=Decimal("5"), price=Decimal("100"), execution_time=DAY1,
        idempotency_hash=f"phase15-fifo-{uuid.uuid4()}",
    )
    trade2 = trade_repo.create_trade(
        user_id=user_id, broker_connection_id=broker_id, instrument_id=instrument_id,
        broker_trade_id="phase15-fifo-buy-2", trade_type="buy",
        quantity=Decimal("10"), price=Decimal("200"), execution_time=DAY2,
        idempotency_hash=f"phase15-fifo-{uuid.uuid4()}",
    )

    lot1 = service.create_holding_lot(
        user_id=user_id, broker_connection_id=broker_id, instrument_id=instrument_id,
        source_trade_id=trade1.id, quantity=Decimal("5"), buy_price=Decimal("100"),
        buy_date=DAY1,
    )
    service.create_holding_lot(
        user_id=user_id, broker_connection_id=broker_id, instrument_id=instrument_id,
        source_trade_id=trade2.id, quantity=Decimal("10"), buy_price=Decimal("200"),
        buy_date=DAY2,
    )
    db_session.flush()

    result = service.consume_lots_fifo(
        user_id=user_id, instrument_id=instrument_id,
        sell_quantity=Decimal("12"), sell_price=Decimal("250"),
        sell_date=DAY2 + timedelta(days=1),
    )
    db_session.commit()

    assert len(result) == 2
    assert result[0]["lot_id"] == lot1.id
    assert result[0]["quantity_consumed"] == Decimal("5")
    assert result[0]["profit_loss"] == Decimal("750")  # (250-100)*5
    assert result[1]["quantity_consumed"] == Decimal("7")
    assert result[1]["profit_loss"] == Decimal("350")  # (250-200)*7
