"""
Corporate action adjustments (Phase 15.1 continuation, priority #8) --
CorporateActionService: split/bonus ratio math. Expected values
independently verified: a stock split or bonus issue must preserve total
cost basis exactly (quantity * price = constant before and after) --
that's the defining property of both corporate action types, not
something read off the code.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.services.corporate_action_service import CorporateActionService
from tests.fakes import FakeCorporateActionRepository, FakeHoldingLotRepository, FakeLot

EARLY = datetime(2024, 1, 1, tzinfo=timezone.utc)
APPLIED_AT = datetime(2025, 1, 1, tzinfo=timezone.utc)


def make_service(lots):
    holding_repo = FakeHoldingLotRepository(lots)
    ca_repo = FakeCorporateActionRepository()
    return CorporateActionService(ca_repo, holding_repo), holding_repo, ca_repo


def test_2_for_1_split_doubles_quantity_and_halves_price():
    """Cost basis check: 10 shares @ Rs.100 = Rs.1000 before. After a 2-for-1
    split, must still be exactly Rs.1000 (20 shares @ Rs.50)."""
    lot = FakeLot(quantity_remaining=Decimal("10"), buy_price=Decimal("100"), buy_date=EARLY, quantity_bought=Decimal("10"))
    service, _, _ = make_service([lot])

    result = service.apply_corporate_action(
        user_id=uuid4(), instrument_id=uuid4(), action_type="stock_split",
        ratio=Decimal("2"), applied_at=APPLIED_AT,
    )

    assert lot.quantity_remaining == Decimal("20")
    assert lot.buy_price == Decimal("50")
    assert lot.quantity_remaining * lot.buy_price == Decimal("1000")  # cost basis preserved exactly
    assert result.lots_adjusted == 1


def test_3_for_1_bonus_issue_math():
    """Bonus issue is functionally identical math to a split for cost-basis
    purposes -- 3x ratio means 3x quantity, 1/3 price."""
    lot = FakeLot(quantity_remaining=Decimal("30"), buy_price=Decimal("300"), buy_date=EARLY, quantity_bought=Decimal("30"))
    service, _, _ = make_service([lot])

    service.apply_corporate_action(
        user_id=uuid4(), instrument_id=uuid4(), action_type="bonus_issue",
        ratio=Decimal("3"), applied_at=APPLIED_AT,
    )

    # 30 * 300 = 9000 before; after: 90 shares @ Rs.100 = 9000
    assert lot.quantity_remaining == Decimal("90")
    assert lot.buy_price == Decimal("100")
    assert lot.quantity_remaining * lot.buy_price == Decimal("9000")


def test_only_lots_bought_before_the_action_date_are_adjusted():
    """A lot bought AFTER the corporate action's applied_at date already
    reflects the post-action price (that's what the broker actually
    charged) -- adjusting it again would double-count the split."""
    old_lot = FakeLot(quantity_remaining=Decimal("10"), buy_price=Decimal("100"), buy_date=EARLY, quantity_bought=Decimal("10"))
    new_lot = FakeLot(
        quantity_remaining=Decimal("10"), buy_price=Decimal("50"),
        buy_date=APPLIED_AT + timedelta(days=1),
        quantity_bought=Decimal("10"),
    )
    service, _, _ = make_service([old_lot, new_lot])

    result = service.apply_corporate_action(
        user_id=uuid4(), instrument_id=uuid4(), action_type="stock_split",
        ratio=Decimal("2"), applied_at=APPLIED_AT,
    )

    assert old_lot.buy_price == Decimal("50")  # adjusted
    assert new_lot.buy_price == Decimal("50")  # untouched, already at post-split price
    assert result.lots_adjusted == 1


def test_invalid_action_type_rejected():
    service, _, _ = make_service([])
    with pytest.raises(ValueError, match="Invalid action type"):
        service.apply_corporate_action(
            user_id=uuid4(), instrument_id=uuid4(), action_type="dividend",
            ratio=Decimal("2"), applied_at=APPLIED_AT,
        )


def test_ratio_of_1_or_less_rejected():
    """A ratio of 1 (no-op) or less than 1 makes no sense for a split/bonus
    (that would be a reverse split, not modeled by these two action
    types) -- must be rejected, not silently applied as a no-op or an
    inverted adjustment."""
    service, _, _ = make_service([])
    with pytest.raises(ValueError, match="Ratio must be greater than 1"):
        service.apply_corporate_action(
            user_id=uuid4(), instrument_id=uuid4(), action_type="stock_split",
            ratio=Decimal("1"), applied_at=APPLIED_AT,
        )
    with pytest.raises(ValueError, match="Ratio must be greater than 1"):
        service.apply_corporate_action(
            user_id=uuid4(), instrument_id=uuid4(), action_type="stock_split",
            ratio=Decimal("0.5"), applied_at=APPLIED_AT,
        )


def test_duplicate_action_for_same_instrument_and_date_rejected():
    """Applying the exact same corporate action twice must be rejected --
    otherwise a double-apply would double the quantity/halve the price
    again, corrupting cost basis."""
    lot = FakeLot(quantity_remaining=Decimal("10"), buy_price=Decimal("100"), buy_date=EARLY, quantity_bought=Decimal("10"))
    instrument_id = uuid4()
    user_id = uuid4()
    service, _, _ = make_service([lot])

    service.apply_corporate_action(
        user_id=user_id, instrument_id=instrument_id, action_type="stock_split",
        ratio=Decimal("2"), applied_at=APPLIED_AT,
    )
    with pytest.raises(ValueError, match="already been applied"):
        service.apply_corporate_action(
            user_id=user_id, instrument_id=instrument_id, action_type="stock_split",
            ratio=Decimal("2"), applied_at=APPLIED_AT,
        )


def test_multiple_lots_all_adjusted_consistently():
    lot1 = FakeLot(quantity_remaining=Decimal("10"), buy_price=Decimal("100"), buy_date=EARLY, quantity_bought=Decimal("10"))
    lot2 = FakeLot(quantity_remaining=Decimal("5"), buy_price=Decimal("100"), buy_date=EARLY, quantity_bought=Decimal("5"))
    service, _, _ = make_service([lot1, lot2])

    result = service.apply_corporate_action(
        user_id=uuid4(), instrument_id=uuid4(), action_type="stock_split",
        ratio=Decimal("2"), applied_at=APPLIED_AT,
    )

    assert result.lots_adjusted == 2
    assert lot1.quantity_remaining == Decimal("20") and lot1.buy_price == Decimal("50")
    assert lot2.quantity_remaining == Decimal("10") and lot2.buy_price == Decimal("50")
