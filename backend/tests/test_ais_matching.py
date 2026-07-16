"""
AIS Reconciliation auto-match engine (Phase 15.1 continuation, priority #1)
-- AisMatchingService.run_match, covering all 5 documented mismatch types
(missing, qty, price, duplicate, TDS) plus matched/unresolved.

Unlike the tax-law tests, AIS matching isn't governed by an external legal
rule -- it's this project's OWN documented heuristic (BRD FR-AIS-03 only
names the 5 mismatch types, not the exact thresholds). "Independently
verified" here means: expected outcomes are hand-computed from the
tolerance/ratio rules stated in ais_matching_service.py's own docstrings
and module constants (MATCH_ABS_TOLERANCE=Rs.1, MATCH_REL_TOLERANCE=1%,
QTY_RATIO_TOLERANCE=2% band around a nice ratio) BEFORE running the code,
not by reading what run_match happens to currently return. If those
constants ever drift from what's tested here, that's a real signal, not
test noise.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.services.ais_matching_service import AisMatchingService
from tests.fakes import FakeAisLine, FakeGain, FakeRealizedGainRepository

AY_START = datetime(2025, 4, 1, tzinfo=timezone.utc)
AY_END = datetime(2026, 4, 1, tzinfo=timezone.utc)


def run(lines, equity_gains=None, crypto_gains=None):
    gains = list(equity_gains or []) + list(crypto_gains or [])
    service = AisMatchingService(realized_gain_repository=FakeRealizedGainRepository(gains))
    return service.run_match(
        user_id=uuid4(), assessment_year="2026-27",
        lines=lines, ay_start=AY_START, ay_end=AY_END,
    )


def equity_gain(sell_price, quantity_sold):
    return FakeGain(
        gain_type="STCG", profit_loss=Decimal("0"), income_type="equity_capital_gains",
        sell_price=Decimal(str(sell_price)), quantity_sold=Decimal(str(quantity_sold)),
    )


def test_matched_when_reported_equals_computed():
    """computed = 1000 shares * 100 = 100000, reported = 100000 -> exact match."""
    lines = [FakeAisLine(section_code="SFT-017 Sale of securities", reported_amount=Decimal("100000"))]
    results = run(lines, equity_gains=[equity_gain(sell_price=100, quantity_sold=1000)])

    assert results[0]["match_status"] == "matched"
    assert results[0]["mismatch_type"] is None


def test_matched_within_absolute_tolerance():
    """diff = 0.50 <= Rs.1.00 absolute tolerance -> still matched, not a false mismatch."""
    lines = [FakeAisLine(section_code="SFT-017 Sale of securities", reported_amount=Decimal("100000.50"))]
    results = run(lines, equity_gains=[equity_gain(sell_price=100, quantity_sold=1000)])

    assert results[0]["match_status"] == "matched"


def test_missing_when_no_computed_data_but_ais_reports_something():
    """No matching realized gains at all (computed=0) but AIS reports a
    positive amount -> 'missing', the case a disconnected/unsynced broker
    produces."""
    lines = [FakeAisLine(section_code="SFT-017 Sale of securities", reported_amount=Decimal("50000"))]
    results = run(lines, equity_gains=[])  # nothing computed

    assert results[0]["match_status"] == "mismatch"
    assert results[0]["mismatch_type"] == "missing"


def test_duplicate_second_line_with_same_section_and_amount():
    """Two lines, same section_code (case/whitespace-insensitive) and same
    reported_amount (quantized to paise) -> the SECOND one is flagged
    duplicate, the first is evaluated normally."""
    lines = [
        FakeAisLine(section_code="SFT-017 Sale of securities", reported_amount=Decimal("100000")),
        FakeAisLine(section_code="  sft-017 sale of securities  ", reported_amount=Decimal("100000.00")),
    ]
    results = run(lines, equity_gains=[equity_gain(sell_price=100, quantity_sold=1000)])

    assert results[0]["match_status"] == "matched"  # first line evaluated normally
    assert results[1]["match_status"] == "mismatch"
    assert results[1]["mismatch_type"] == "duplicate"


def test_tds_category_always_flagged_regardless_of_amount():
    """Section/description containing TDS keywords short-circuits straight
    to mismatch_type='TDS', even though nothing here would otherwise fail
    to match (no computed-vs-reported comparison even happens)."""
    lines = [FakeAisLine(section_code="TDS-194Q", reported_amount=Decimal("5000"), description="Tax Deducted at Source")]
    results = run(lines)

    assert results[0]["match_status"] == "mismatch"
    assert results[0]["mismatch_type"] == "TDS"


def test_qty_mismatch_when_ratio_is_a_nice_multiple():
    """computed=200000, reported=100000 -> ratio exactly 2.0, within the 2%
    band around the documented 'nice ratio' 2 -> classified 'qty' (a
    plausible unit-count/split issue), not 'price'."""
    lines = [FakeAisLine(section_code="SFT-017 Sale of securities", reported_amount=Decimal("100000"))]
    results = run(lines, equity_gains=[equity_gain(sell_price=100, quantity_sold=2000)])  # computed = 200000

    assert results[0]["match_status"] == "mismatch"
    assert results[0]["mismatch_type"] == "qty"


def test_price_mismatch_when_ratio_is_not_a_nice_multiple():
    """computed=100000, reported=85000 -> ratio ~1.176, not within 2% of any
    documented nice ratio [2, 0.5, 3, 1/3, 4, 0.25] -> classified 'price'."""
    lines = [FakeAisLine(section_code="SFT-017 Sale of securities", reported_amount=Decimal("85000"))]
    results = run(lines, equity_gains=[equity_gain(sell_price=100, quantity_sold=1000)])  # computed = 100000

    assert results[0]["match_status"] == "mismatch"
    assert results[0]["mismatch_type"] == "price"


def test_unresolved_when_category_cannot_be_detected():
    """Section code/description matches none of the equity/crypto/TDS
    keyword lists -> 'unresolved', never silently guessed as matched."""
    lines = [FakeAisLine(section_code="XYZ-999", reported_amount=Decimal("10000"), description="Unrecognized SFT code")]
    results = run(lines)

    assert results[0]["match_status"] == "unresolved"
    assert results[0]["mismatch_type"] is None


def test_crypto_category_computed_independently_of_equity():
    """A crypto-labeled line must be compared against crypto-only computed
    totals, not accidentally pooled with equity gains."""
    lines = [FakeAisLine(section_code="SFT-021", reported_amount=Decimal("50000"), description="Sale of Virtual Digital Assets")]
    equity = [equity_gain(sell_price=100, quantity_sold=1000)]  # 100000, irrelevant to this line
    crypto = [FakeGain(
        gain_type=None, profit_loss=Decimal("0"), income_type="crypto_vda",
        sell_price=Decimal("50000"), quantity_sold=Decimal("1"),
    )]
    results = run(lines, equity_gains=equity, crypto_gains=crypto)

    assert results[0]["match_status"] == "matched"
