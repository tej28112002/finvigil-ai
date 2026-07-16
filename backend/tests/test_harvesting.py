"""
Tax-loss harvesting calculations (Phase 15.1 priority #4) --
HarvestingService.get_harvest_candidates / get_harvest_summary.

Pure unit tests via FakeHoldingLotRepository + FakePriceService (tests/
fakes.py) -- no DB, no network. Expected values hand-computed
independently from qty/price inputs, same STCG/LTCG rates verified in
test_tax_classification.py (20% / 12.5%, Rs.1,25,000 exemption).
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.services.harvesting_service import HarvestingService
from tests.fakes import (
    FakeGain,
    FakeHoldingLotRepository,
    FakeInstrument,
    FakeLot,
    FakePriceService,
    FakeRealizedGainRepository,
)

NOW = datetime.now(timezone.utc)


def make_service(lots, prices, existing_gains=None):
    holding_repo = FakeHoldingLotRepository(lots)
    gain_repo = FakeRealizedGainRepository(existing_gains or [])
    price_service = FakePriceService(prices)
    return HarvestingService(
        holding_repository=holding_repo,
        realized_gain_repository=gain_repo,
        price_service=price_service,
    )


def make_lot(symbol, qty, buy_price, days_ago):
    return FakeLot(
        quantity_remaining=Decimal(str(qty)),
        buy_price=Decimal(str(buy_price)),
        buy_date=NOW - timedelta(days=days_ago),
        instrument=FakeInstrument(symbol=symbol),
    )


def test_only_lots_below_cost_basis_are_candidates():
    """A lot currently worth MORE than its buy price must never appear --
    only unrealized losses are harvest candidates."""
    losing_lot = make_lot("LOSER", qty=10, buy_price=100, days_ago=30)
    winning_lot = make_lot("WINNER", qty=10, buy_price=100, days_ago=30)
    service = make_service(
        [losing_lot, winning_lot],
        prices={"LOSER": {"last_price": Decimal("80")}, "WINNER": {"last_price": Decimal("120")}},
    )

    candidates = service.get_harvest_candidates(user_id=None, assessment_year="2026-27")

    assert len(candidates) == 1
    assert candidates[0]["symbol"] == "LOSER"
    assert candidates[0]["unrealized_loss"] == Decimal("-200")  # (80-100)*10


def test_stcg_candidate_tax_saving_is_20_percent_of_loss():
    lot = make_lot("SHORT", qty=10, buy_price=100, days_ago=30)  # well under 365 days
    service = make_service([lot], prices={"SHORT": {"last_price": Decimal("90")}})

    candidates = service.get_harvest_candidates(user_id=None, assessment_year="2026-27")

    assert candidates[0]["gain_type"] == "STCG"
    # loss = (90-100)*10 = -100, magnitude 100, saving = 100*0.20 = 20
    assert candidates[0]["estimated_tax_saving"] == Decimal("20.0")


def test_ltcg_candidate_saving_is_zero_without_existing_taxable_ltcg_base():
    """
    If the user's already-realized LTCG for the AY is at/below the
    Rs.1,25,000 exemption, harvesting more LTCG loss saves Rs.0 in tax this
    year -- there's no taxable LTCG base left for it to offset. Must not
    claim a fake 12.5% saving.
    """
    lot = make_lot("LONG", qty=10, buy_price=1000, days_ago=400)  # > 365 days -> LTCG
    existing_gains = [FakeGain(gain_type="LTCG", profit_loss=Decimal("50000"))]  # under 125000
    service = make_service(
        [lot], prices={"LONG": {"last_price": Decimal("900")}}, existing_gains=existing_gains
    )

    candidates = service.get_harvest_candidates(user_id=None, assessment_year="2026-27")

    assert candidates[0]["gain_type"] == "LTCG"
    assert candidates[0]["estimated_tax_saving"] == Decimal("0")


def test_ltcg_candidate_saving_is_12_5_percent_with_existing_taxable_base():
    """Existing realized LTCG already exceeds the exemption -> every rupee
    of new harvested loss saves the full 12.5%."""
    lot = make_lot("LONG", qty=10, buy_price=1000, days_ago=400)
    existing_gains = [FakeGain(gain_type="LTCG", profit_loss=Decimal("200000"))]  # over 125000
    service = make_service(
        [lot], prices={"LONG": {"last_price": Decimal("900")}}, existing_gains=existing_gains
    )

    candidates = service.get_harvest_candidates(user_id=None, assessment_year="2026-27")

    # loss magnitude = (1000-900)*10 = 1000, saving = 1000*0.125 = 125
    assert candidates[0]["estimated_tax_saving"] == Decimal("125.000")


def test_price_estimate_fallback_never_produces_false_positive_loss():
    """No live price available -> falls back to cost basis. current_price
    == buy_price means zero loss, so this lot must NOT appear as a
    candidate -- the engine must never fabricate a loss it can't observe."""
    lot = make_lot("NOPRICE", qty=10, buy_price=100, days_ago=30)
    service = make_service([lot], prices={})  # symbol not returned by price service

    candidates = service.get_harvest_candidates(user_id=None, assessment_year="2026-27")

    assert candidates == []


def test_candidates_sorted_by_tax_saving_descending():
    small = make_lot("SMALL", qty=1, buy_price=100, days_ago=30)
    big = make_lot("BIG", qty=100, buy_price=100, days_ago=30)
    service = make_service(
        [small, big],
        prices={"SMALL": {"last_price": Decimal("90")}, "BIG": {"last_price": Decimal("90")}},
    )

    candidates = service.get_harvest_candidates(user_id=None, assessment_year="2026-27")

    assert [c["symbol"] for c in candidates] == ["BIG", "SMALL"]


def test_summary_aggregates_match_hand_computed_totals():
    lot1 = make_lot("A", qty=10, buy_price=100, days_ago=30)   # STCG loss 100, saving 20
    lot2 = make_lot("B", qty=5, buy_price=200, days_ago=30)    # STCG loss 250, saving 50
    service = make_service(
        [lot1, lot2],
        prices={"A": {"last_price": Decimal("90")}, "B": {"last_price": Decimal("150")}},
    )

    summary = service.get_harvest_summary(user_id=None, assessment_year="2026-27")

    assert summary["candidate_count"] == 2
    assert summary["total_harvestable_loss"] == Decimal("-350")  # -100 + -250
    assert summary["total_estimated_tax_saving"] == Decimal("70.0")  # 20 + 50
