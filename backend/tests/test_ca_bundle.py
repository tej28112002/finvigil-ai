"""
CA Export ZIP Bundle (Phase 15.1 continuation, priority #3) --
CABundleService.generate_bundle. Verifies the ZIP contains exactly the
right files with correct content, not just "does it not crash".

Integration test against the real DB, read-only against the primary test
user's existing data (never mutated) via the db_session fixture, which
never commits -- the two ca_export_jobs audit rows this call legitimately
creates as a side effect are rolled back automatically, same safe pattern
used in test_tax_classification.py's real-DB tests.

Uses AY 2026-27 specifically because that's the only assessment year with
both (a) an active itr_schema_mapping and (b) an existing tax_summary row
for the primary test user -- both are hard requirements of the services
CABundleService composes. Expected LTCG figure (2000, well under the
Rs.1,25,000 exemption) was independently hand-verified in
test_tax_classification.py already.
"""
import io
import zipfile
import json

from tests.conftest import PRIMARY_TEST_USER


def build_real_service(db_session):
    import uuid as uuid_module

    from app.repositories.broker_connection_repository import BrokerConnectionRepository
    from app.repositories.ca_export_job_repository import CaExportJobRepository
    from app.repositories.holding_lot_repository import HoldingLotRepository
    from app.repositories.instrument_repository import InstrumentRepository
    from app.repositories.itr_schema_repository import ItrSchemaRepository
    from app.repositories.realized_gain_repository import RealizedGainRepository
    from app.repositories.tax_summary_repository import TaxSummaryRepository
    from app.repositories.vault_repository import VaultRepository
    from app.services.ca_bundle_service import CABundleService
    from app.services.harvesting_service import HarvestingService
    from app.services.itr3_export_service import ITR3ExportService
    from app.services.price_service import PriceService
    from app.services.tax_export_service import TaxExportService

    realized_gain_repo = RealizedGainRepository(db_session)
    instrument_repo = InstrumentRepository(db_session)
    tax_summary_repo = TaxSummaryRepository(db_session)
    ca_export_job_repo = CaExportJobRepository(db_session)
    holding_lot_repo = HoldingLotRepository(db_session)

    itr3_service = ITR3ExportService(
        itr_schema_repository=ItrSchemaRepository(db_session),
        realized_gain_repository=realized_gain_repo,
        tax_summary_repository=tax_summary_repo,
        instrument_repository=instrument_repo,
    )
    tax_export_service = TaxExportService(
        tax_summary_repository=tax_summary_repo,
        realized_gain_repository=realized_gain_repo,
        ca_export_job_repository=ca_export_job_repo,
        instrument_repository=instrument_repo,
    )
    price_service = PriceService(
        broker_connection_repository=BrokerConnectionRepository(db_session),
        vault_repository=VaultRepository(db_session),
    )
    harvesting_service = HarvestingService(
        holding_repository=holding_lot_repo,
        realized_gain_repository=realized_gain_repo,
        price_service=price_service,
    )

    return CABundleService(
        itr3_export_service=itr3_service,
        tax_export_service=tax_export_service,
        realized_gain_repository=realized_gain_repo,
        instrument_repository=instrument_repo,
        harvesting_service=harvesting_service,
        ca_export_job_repository=ca_export_job_repo,
        holding_lot_repository=holding_lot_repo,
    ), uuid_module.UUID(PRIMARY_TEST_USER)


def test_zip_contains_exactly_the_six_expected_files(db_session):
    service, user_id = build_real_service(db_session)

    zip_bytes = service.generate_bundle(user_id=user_id, assessment_year="2026-27")

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = set(zf.namelist())

    assert names == {
        "itr3_schedules.json",
        "capital_gains_summary.json",
        "realized_gains.csv",
        "harvest_opportunities.json",
        "holdings.csv",
        "README.txt",
    }


def test_realized_gains_csv_contains_the_known_ltcg_row(db_session):
    """
    Independently verified in test_tax_classification.py: this user's
    AY 2026-27 has one equity realized gain, LTCG, profit_loss=2000.

    The CSV covers BOTH equity_capital_gains and crypto_vda for this AY
    (_INCOME_TYPES_FOR_CSV in ca_bundle_service.py), so this user's 3
    crypto_vda rows sharing the same AY are also expected here -- this
    test only asserts the specific known equity row is present and
    correct among however many rows exist, not the total row count.
    """
    service, user_id = build_real_service(db_session)

    zip_bytes = service.generate_bundle(user_id=user_id, assessment_year="2026-27")

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_text = zf.read("realized_gains.csv").decode("utf-8")

    lines = csv_text.strip().splitlines()
    assert lines[0] == "symbol,isin,quantity_sold,buy_date,sell_date,buy_price,sell_price,holding_days,gain_type,profit_loss"
    reliance_rows = [row for row in lines[1:] if row.startswith("RELIANCE,")]
    assert len(reliance_rows) == 1
    assert reliance_rows[0].endswith(",LTCG,2000.00000000")


def test_itr3_schedules_json_matches_independently_verified_ltcg_total(db_session):
    service, user_id = build_real_service(db_session)

    zip_bytes = service.generate_bundle(user_id=user_id, assessment_year="2026-27")

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        itr3 = json.loads(zf.read("itr3_schedules.json"))

    schedule = itr3["ITR"]["ITR3"]["Schedule112A"]
    # Matches test_tax_classification.py's independently hand-verified
    # AY 2026-27 total_ltcg_gains = 2000.
    assert schedule["LTCGBeforelowerB1B2112A"] == 2000
    assert isinstance(schedule["LTCGBeforelowerB1B2112A"], int)
    # 2000 well under the 125000 exemption -> zero taxable balance.
    assert schedule["Balance112A"] == 0


def test_holdings_csv_contains_open_reliance_lot(db_session):
    """
    holdings.csv must be present, have the right header, contain at least
    one RELIANCE row, and have cost_basis_total = quantity_remaining * buy_price
    for every row (verifies the math, not hardcoded DB quantities which vary
    across test data seeds).
    """
    service, user_id = build_real_service(db_session)

    zip_bytes = service.generate_bundle(user_id=user_id, assessment_year="2026-27")

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_text = zf.read("holdings.csv").decode("utf-8")

    lines = csv_text.strip().splitlines()
    assert lines[0] == "symbol,isin,buy_date,quantity_remaining,buy_price,cost_basis_total,status"
    reliance_rows = [r for r in lines[1:] if r.startswith("RELIANCE,")]
    assert len(reliance_rows) >= 1

    from decimal import Decimal
    for row in lines[1:]:
        parts = row.split(",")
        qty = Decimal(parts[3])
        price = Decimal(parts[4])
        cost_basis = Decimal(parts[5])
        assert cost_basis == qty * price, (
            f"cost_basis_total mismatch: {cost_basis} != {qty} * {price} in row: {row}"
        )


def test_readme_and_capital_gains_summary_are_present_and_readable(db_session):
    service, user_id = build_real_service(db_session)

    zip_bytes = service.generate_bundle(user_id=user_id, assessment_year="2026-27")

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        readme = zf.read("README.txt").decode("utf-8")
        summary = json.loads(zf.read("capital_gains_summary.json"))

    assert "2026-27" in readme
    assert "Not a complete ITR-3 filing" in readme
    assert summary["assessment_year"] == "2026-27"
    assert "summary" in summary
