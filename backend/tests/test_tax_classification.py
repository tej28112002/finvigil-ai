"""
STCG/LTCG rates, exemption, and TaxEngineService.calculate_tax_summary's
computation — Phase 15.1 priority #2.

Rate/exemption values below (20% STCG, 12.5% LTCG, Rs.1,25,000 exemption)
are NOT copied from tax_engine_service.py -- they're independently sourced
from India's actual capital-gains tax law after Budget 2024 (effective
23 Jul 2024, applicable for AY 2025-26 onward, which covers this project's
target AY 2026-27 / FY 2025-26): STCG on listed equity raised 15% -> 20%,
LTCG raised 10% -> 12.5%, exemption raised Rs.1,00,000 -> Rs.1,25,000. If
the code and this independently-sourced figure ever disagree, the test
should fail -- that's the point.
"""
from decimal import Decimal
from uuid import uuid4

import pytest

from app.services.tax_engine_service import TaxEngineService
from tests.conftest import PRIMARY_TEST_USER
from tests.fakes import FakeGain, FakeRealizedGainRepository, FakeTaxSummaryRepository

# Independently-sourced ground truth (Budget 2024 equity capital gains
# regime), not read from the module under test.
EXPECTED_STCG_RATE = Decimal("0.20")
EXPECTED_LTCG_RATE = Decimal("0.125")
EXPECTED_LTCG_EXEMPTION = Decimal("125000")


def make_service(gains: list[FakeGain]):
    gain_repo = FakeRealizedGainRepository(gains)
    summary_repo = FakeTaxSummaryRepository()
    return TaxEngineService(
        tax_summary_repository=summary_repo,
        realized_gain_repository=gain_repo,
    ), summary_repo


def test_rates_and_exemption_match_independently_sourced_law():
    """Not a self-check against the code's own constants -- these are the
    real Budget 2024 figures, typed in independently above."""
    service, summary_repo = make_service([])
    result = service.calculate_tax_summary(user_id=uuid4(), assessment_year="2026-27")
    assert Decimal(str(summary_repo.upserted["stcg_tax_rate"])) == EXPECTED_STCG_RATE
    assert Decimal(str(summary_repo.upserted["ltcg_tax_rate"])) == EXPECTED_LTCG_RATE
    assert Decimal(str(summary_repo.upserted["ltcg_exemption"])) == EXPECTED_LTCG_EXEMPTION


def test_pure_stcg_gain_taxed_at_20_percent_no_exemption():
    """STCG has no exemption -- the full gain is taxable."""
    gains = [FakeGain(gain_type="STCG", profit_loss=Decimal("100000"))]
    service, summary_repo = make_service(gains)
    service.calculate_tax_summary(user_id=uuid4(), assessment_year="2026-27")

    # Hand-computed: 100000 * 0.20 = 20000
    assert Decimal(str(summary_repo.upserted["taxable_stcg"])) == Decimal("100000")
    assert Decimal(str(summary_repo.upserted["stcg_tax"])) == Decimal("20000.000")
    assert Decimal(str(summary_repo.upserted["total_tax_liability"])) == Decimal("20000.000")


def test_pure_ltcg_gain_under_exemption_is_tax_free():
    """LTCG below Rs.1,25,000 for the year owes zero tax."""
    gains = [FakeGain(gain_type="LTCG", profit_loss=Decimal("100000"))]
    service, summary_repo = make_service(gains)
    service.calculate_tax_summary(user_id=uuid4(), assessment_year="2026-27")

    assert Decimal(str(summary_repo.upserted["taxable_ltcg"])) == Decimal("0")
    assert Decimal(str(summary_repo.upserted["ltcg_tax"])) == Decimal("0")


def test_pure_ltcg_gain_over_exemption_taxed_on_excess_only():
    """LTCG of 200000: only (200000 - 125000) = 75000 is taxable, at 12.5%."""
    gains = [FakeGain(gain_type="LTCG", profit_loss=Decimal("200000"))]
    service, summary_repo = make_service(gains)
    service.calculate_tax_summary(user_id=uuid4(), assessment_year="2026-27")

    # Hand-computed: (200000 - 125000) * 0.125 = 75000 * 0.125 = 9375
    assert Decimal(str(summary_repo.upserted["taxable_ltcg"])) == Decimal("75000")
    assert Decimal(str(summary_repo.upserted["ltcg_tax"])) == Decimal("9375.000")


def test_multiple_gains_of_same_type_sum_correctly():
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("30000")),
        FakeGain(gain_type="STCG", profit_loss=Decimal("20000")),
    ]
    service, summary_repo = make_service(gains)
    service.calculate_tax_summary(user_id=uuid4(), assessment_year="2026-27")

    assert Decimal(str(summary_repo.upserted["total_stcg_gains"])) == Decimal("50000")
    assert Decimal(str(summary_repo.upserted["stcg_tax"])) == Decimal("10000.000")  # 50000*0.20


class TestAgainstRealTestUserData:
    """
    Integration tests, read-only against the documented primary test user's
    EXISTING realized_gains — never creates, modifies, or deletes any of
    that user's rows. calculate_tax_summary's own upsert is idempotent
    (recomputes the same value from the same unchanged input rows every
    time), so calling it here doesn't corrupt anything.

    Expected values below were hand-verified independently by querying this
    user's real equity_capital_gains rows directly and computing the AY
    bucketing + tax math by hand before writing these assertions -- not
    derived by running the code and copying its output.

    AY 2025-26: two STCG rows, 500 + 200 = 700 total STCG, 0 LTCG.
      taxable_stcg = 700, stcg_tax = 700*0.20 = 140.00. No LTCG, no set-off.
    AY 2026-27: one LTCG row, 2000, 0 STCG.
      2000 < 125000 exemption -> taxable_ltcg = 0, ltcg_tax = 0. total = 0.
    """

    def test_ay_2025_26_stcg_total(self, db_session):
        from app.repositories.realized_gain_repository import RealizedGainRepository
        from app.repositories.tax_summary_repository import TaxSummaryRepository
        import uuid as uuid_module

        service = TaxEngineService(
            tax_summary_repository=TaxSummaryRepository(db_session),
            realized_gain_repository=RealizedGainRepository(db_session),
        )
        summary = service.calculate_tax_summary(
            user_id=uuid_module.UUID(PRIMARY_TEST_USER), assessment_year="2025-26"
        )
        assert Decimal(str(summary.total_stcg_gains)) == Decimal("700.00000000")
        assert Decimal(str(summary.total_ltcg_gains)) == Decimal("0")
        assert Decimal(str(summary.total_tax_liability)) == Decimal("140.000")

    def test_ay_2026_27_ltcg_under_exemption(self, db_session):
        from app.repositories.realized_gain_repository import RealizedGainRepository
        from app.repositories.tax_summary_repository import TaxSummaryRepository
        import uuid as uuid_module

        service = TaxEngineService(
            tax_summary_repository=TaxSummaryRepository(db_session),
            realized_gain_repository=RealizedGainRepository(db_session),
        )
        summary = service.calculate_tax_summary(
            user_id=uuid_module.UUID(PRIMARY_TEST_USER), assessment_year="2026-27"
        )
        assert Decimal(str(summary.total_ltcg_gains)) == Decimal("2000.00000000")
        assert Decimal(str(summary.total_tax_liability)) == Decimal("0.000")
