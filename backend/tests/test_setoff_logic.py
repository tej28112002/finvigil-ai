"""
Capital-loss set-off rules (Phase 15.1 priority #3) -- Section 70 of the
Income Tax Act, 1961, independently verified against the Income Tax
Department and cross-referenced against a second source before writing
these tests (not inferred from tax_engine_service.py's own logic):

  - Short-term capital LOSS can be set off against BOTH short-term AND
    long-term capital GAINS.
  - Long-term capital LOSS can ONLY be set off against long-term capital
    GAINS -- never against short-term gains.

This asymmetry is the crux of this file. tax_engine_service.py's current
set-off branches treat the two cases as symmetric mirror images of each
other, which is correct for the STCG-loss-offsets-LTCG-gain case but
WRONG for the LTCG-loss-offsets-STCG-gain case. The test below encoding
the correct (asymmetric) rule is expected to FAIL against the current
implementation -- that failure is the actual finding, not a mistake in
the test.
"""
from decimal import Decimal
from uuid import uuid4

from app.services.tax_engine_service import TaxEngineService
from tests.fakes import FakeGain, FakeRealizedGainRepository, FakeTaxSummaryRepository


def make_service(gains: list[FakeGain]):
    gain_repo = FakeRealizedGainRepository(gains)
    summary_repo = FakeTaxSummaryRepository()
    return TaxEngineService(
        tax_summary_repository=summary_repo,
        realized_gain_repository=gain_repo,
    ), summary_repo


def test_stcg_loss_correctly_offsets_ltcg_gain():
    """Allowed under Section 70: a short-term loss reduces a long-term gain."""
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("-30000")),
        FakeGain(gain_type="LTCG", profit_loss=Decimal("200000")),
    ]
    service, summary_repo = make_service(gains)
    service.calculate_tax_summary(user_id=uuid4(), assessment_year="2026-27")

    # Hand-computed: net_ltcg = 200000 - 30000 = 170000
    # taxable_ltcg = 170000 - 125000 (exemption) = 45000
    # ltcg_tax = 45000 * 0.125 = 5625; stcg_tax = 0 (fully absorbed)
    assert Decimal(str(summary_repo.upserted["taxable_stcg"])) == Decimal("0")
    assert Decimal(str(summary_repo.upserted["taxable_ltcg"])) == Decimal("45000")
    assert Decimal(str(summary_repo.upserted["ltcg_tax"])) == Decimal("5625")


def test_ltcg_loss_must_not_offset_stcg_gain_section_70():
    """
    NOT allowed under Section 70: a long-term loss must NOT reduce a
    short-term gain. The STCG gain stays fully taxable; the LTCG loss earns
    no set-off this year (in reality it would carry forward up to 8 years,
    which this engine doesn't model -- out of scope here, only the current-
    year figure is being checked).

    Hand-computed correct result: STCG gain of 50000 is fully taxable
    (no valid loss to offset it) -> taxable_stcg = 50000, stcg_tax =
    50000*0.20 = 10000. The 20000 LTCG loss must NOT appear in taxable_stcg
    at all.
    """
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("50000")),
        FakeGain(gain_type="LTCG", profit_loss=Decimal("-20000")),
    ]
    service, summary_repo = make_service(gains)
    service.calculate_tax_summary(user_id=uuid4(), assessment_year="2026-27")

    assert Decimal(str(summary_repo.upserted["taxable_stcg"])) == Decimal("50000"), (
        "BUG: LTCG loss is incorrectly reducing the STCG gain. Section 70 "
        "only allows a long-term loss to offset long-term gains, never "
        "short-term gains. See tax_engine_service.py's "
        "'elif total_ltcg < 0 and total_stcg > 0' branch."
    )
    assert Decimal(str(summary_repo.upserted["stcg_tax"])) == Decimal("10000")


def test_both_gains_no_offset_needed():
    """Same-sign case: straightforward addition, no set-off branch triggers."""
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("10000")),
        FakeGain(gain_type="LTCG", profit_loss=Decimal("50000")),
    ]
    service, summary_repo = make_service(gains)
    service.calculate_tax_summary(user_id=uuid4(), assessment_year="2026-27")

    assert Decimal(str(summary_repo.upserted["taxable_stcg"])) == Decimal("10000")
    # LTCG 50000 is under the 125000 exemption -> 0 taxable
    assert Decimal(str(summary_repo.upserted["taxable_ltcg"])) == Decimal("0")


def test_both_losses_nothing_taxable():
    """No gains at all -- both taxable amounts must floor at zero, not go
    negative (max(0, ...) guard in the code)."""
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("-5000")),
        FakeGain(gain_type="LTCG", profit_loss=Decimal("-8000")),
    ]
    service, summary_repo = make_service(gains)
    service.calculate_tax_summary(user_id=uuid4(), assessment_year="2026-27")

    assert Decimal(str(summary_repo.upserted["taxable_stcg"])) == Decimal("0")
    assert Decimal(str(summary_repo.upserted["taxable_ltcg"])) == Decimal("0")
    assert Decimal(str(summary_repo.upserted["total_tax_liability"])) == Decimal("0")


def test_stcg_loss_larger_than_ltcg_gain_leaves_zero_not_negative():
    """STCG loss bigger than the LTCG gain it's offsetting -- net_ltcg goes
    negative, taxable_ltcg must floor at 0 (max(0,...) guard), not report a
    negative tax."""
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("-100000")),
        FakeGain(gain_type="LTCG", profit_loss=Decimal("40000")),
    ]
    service, summary_repo = make_service(gains)
    service.calculate_tax_summary(user_id=uuid4(), assessment_year="2026-27")

    assert Decimal(str(summary_repo.upserted["taxable_ltcg"])) == Decimal("0")
    assert Decimal(str(summary_repo.upserted["total_tax_liability"])) == Decimal("0")
