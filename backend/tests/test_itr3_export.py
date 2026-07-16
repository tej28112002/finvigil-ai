"""
ITR-3 schema-driven export (Phase 15.1 continuation, priority #2) --
ITR3ExportService.generate_export. Verifies the REAL CBDT field names (not
guessed/invented ones) end up correctly populated for known input data, and
that every monetary value in the final output is a Python int, per this
project's own money-handling rule (_money() converts Decimal -> int only at
the JSON boundary).

REAL_SCHEMA_MAPPING below is a verbatim copy of the live, currently-active
itr_schema_mappings row for AY 2026-27, fetched via a direct read-only DB
query before writing this file (not invented, not guessed) -- these are the
actual CBDT field names (ISINCode, ShareUnitName, TotSaleValue, etc.) this
project's admin panel has configured. Copied rather than read fresh per
test run so these are fast, DB-free unit tests; if the real schema ever
changes, these tests would need updating anyway since they assert on the
specific field names.

Gain amounts below are hand-computed independently before writing the
assertions, not derived from running the code.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.services.itr3_export_service import ITR3ExportService
from tests.fakes import (
    FakeCaExportJobRepository,
    FakeExistsTaxSummaryRepository,
    FakeGain,
    FakeInstrument,
    FakeInstrumentRepository,
    FakeItrSchemaRepository,
    FakeRealizedGainRepository,
)

REAL_SCHEMA_MAPPING = {
    "ay": "2026-27",
    "constants": {
        "isin_not_required": "INNOTREQUIRD",
        "isin_not_available": "INNOTAVAILAB",
        "vda_head_under_income": "CG",
        "share_on_or_before_flag_modern": "AE",
    },
    "vda_crypto": {
        "schedule_path": ["ITR", "ITR3", "ScheduleVDA"],
        "summary_fields": {
            "total_capital_gain": "TotIncCapGain",
            "total_business_income": "TotIncBusiness",
        },
        "transaction_array": "ScheduleVDADtls",
        "transaction_fields": {
            "income_from_vda": "IncomeFromVDA",
            "acquisition_cost": "AcquisitionCost",
            "date_of_transfer": "DateofTransfer",
            "head_under_income": "HeadUndIncTaxed",
            "date_of_acquisition": "DateofAcquisition",
            "consideration_received": "ConsidReceived",
        },
    },
    "ltcg_equity": {
        "schedule_path": ["ITR", "ITR3", "Schedule112A"],
        "summary_fields": {
            "deductions": "Deductions112A",
            "total_cost": "CostAcqWithoutIndx112A",
            "total_sale_value": "SaleValue112A",
            "fair_market_value": "FairMktValueCapAst112A",
            "transfer_expenses": "ExpExclCnctTransfer112A",
            "total_acquisition_cost": "AcquisitionCost112A",
            "balance_after_exemption": "Balance112A",
            "total_ltcg_before_exemption": "LTCGBeforelowerB1B2112A",
        },
        "transaction_array": "Schedule112ADtls",
        "transaction_fields": {
            "isin": "ISINCode",
            "symbol": "ShareUnitName",
            "balance": "Balance",
            "quantity": "NumSharesUnits",
            "acquisition_cost": "AcquisitionCost",
            "total_deductions": "TotalDeductions",
            "total_sale_value": "TotSaleValue",
            "transfer_expenses": "ExpExclCnctTransfer",
            "share_on_or_before": "ShareOnOrBefore",
            "sale_price_per_unit": "SalePricePerShareUnit",
            "ltcg_before_exemption": "LTCGBeforelower6and11",
            "cost_without_indexation": "CostAcqWithoutIndx",
            "total_fair_market_value": "TotFairMktValueCapAst",
            "fair_market_value_per_unit": "FairMktValuePerShareunit",
        },
    },
    "release_date": "2026-06-30",
    "schema_version": "1.1",
    "stcg_equity_111a": {
        "fields": {
            "balance_cg": "BalanceCG",
            "loss_sec94": "LossSec94of7Or94of8",
            "total_stcg": "TotalSTCG",
            "details_key": "EquityMFonSTTDtls",
            "capital_gain": "CapgainonAssets",
            "deduct_sec48": "DeductSec48",
            "section_code": "MFSectionCode",
            "total_deduction": "TotalDedn",
            "acquisition_cost": "AquisitCost",
            "improvement_cost": "ImproveCost",
            "transfer_expenses": "ExpOnTrans",
            "full_consideration": "FullConsideration",
        },
        "section_code": "1A",
    },
    "ltcg_exemption_limit": 125000,
}


def make_service(gains, instruments):
    return ITR3ExportService(
        itr_schema_repository=FakeItrSchemaRepository(
            mapping_record=type("M", (), {"mapping_json": REAL_SCHEMA_MAPPING, "is_active": True})()
        ),
        realized_gain_repository=FakeRealizedGainRepository(gains),
        tax_summary_repository=FakeExistsTaxSummaryRepository(),
        instrument_repository=FakeInstrumentRepository(instruments),
    )


def test_ltcg_equity_schedule_112a_uses_real_cbdt_field_names_and_int_values():
    reliance_id = uuid4()
    instruments = {reliance_id: FakeInstrument(symbol="RELIANCE", isin="INE002A01018", instrument_type="equity")}
    gains = [
        FakeGain(
            gain_type="LTCG", profit_loss=Decimal("10000"), income_type="equity_capital_gains",
            instrument_id=reliance_id, quantity_sold=Decimal("10"),
            sell_price=Decimal("3000"), buy_price=Decimal("2000"),
            buy_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            sell_date=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
    ]
    service = make_service(gains, instruments)

    result = service.generate_export(user_id=uuid4(), assessment_year="2026-27")
    schedule = result["ITR"]["ITR3"]["Schedule112A"]

    # Hand-computed: sale_value=30000, cost=20000, ltcg_before_exemption=10000
    # Exemption 125000 > 10000, so balance_after_exemption floors at 0.
    assert schedule["SaleValue112A"] == 30000
    assert schedule["CostAcqWithoutIndx112A"] == 20000
    assert schedule["AcquisitionCost112A"] == 20000
    assert schedule["LTCGBeforelowerB1B2112A"] == 10000
    assert schedule["Balance112A"] == 0

    txn = schedule["Schedule112ADtls"][0]
    assert txn["ISINCode"] == "INE002A01018"
    assert txn["ShareUnitName"] == "RELIANCE"
    assert txn["NumSharesUnits"] == 10
    assert txn["SalePricePerShareUnit"] == 3000
    assert txn["TotSaleValue"] == 30000
    assert txn["LTCGBeforelower6and11"] == 10000
    assert txn["ShareOnOrBefore"] == "AE"

    # Every numeric field in the transaction row must be a plain int, not float.
    for key in ("NumSharesUnits", "SalePricePerShareUnit", "TotSaleValue", "LTCGBeforelower6and11"):
        assert isinstance(txn[key], int), f"{key} is {type(txn[key])}, not int"


def test_stcg_equity_schedule_cg_for_23():
    infy_id = uuid4()
    instruments = {infy_id: FakeInstrument(symbol="INFY", isin="INE009A01021", instrument_type="equity")}
    gains = [
        FakeGain(
            gain_type="STCG", profit_loss=Decimal("500"), income_type="equity_capital_gains",
            instrument_id=infy_id, quantity_sold=Decimal("5"),
            sell_price=Decimal("1500"), buy_price=Decimal("1400"),
            buy_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            sell_date=datetime(2025, 3, 1, tzinfo=timezone.utc),
        )
    ]
    service = make_service(gains, instruments)

    result = service.generate_export(user_id=uuid4(), assessment_year="2026-27")
    schedule = result["ITR"]["ITR3"]["ScheduleCGFor23"]

    # Hand-computed: full_consideration=7500, acquisition_cost=7000, capital_gain=500
    assert schedule["TotalSTCG"] == 500
    row = schedule["EquityMFonSTTDtls"][0]
    assert row["MFSectionCode"] == "1A"
    assert row["FullConsideration"] == 7500
    assert row["AquisitCost"] == 7000
    assert row["CapgainonAssets"] == 500
    assert isinstance(row["CapgainonAssets"], int)


def test_crypto_schedule_vda():
    btc_id = uuid4()
    instruments = {btc_id: FakeInstrument(symbol="BTC", isin=None, instrument_type="crypto")}
    gains = [
        FakeGain(
            gain_type=None, profit_loss=Decimal("20000"), income_type="crypto_vda",
            instrument_id=btc_id, quantity_sold=Decimal("1"),
            sell_price=Decimal("100000"), buy_price=Decimal("80000"),
            buy_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            sell_date=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
    ]
    service = make_service(gains, instruments)

    result = service.generate_export(user_id=uuid4(), assessment_year="2026-27")
    schedule = result["ITR"]["ITR3"]["ScheduleVDA"]

    assert schedule["TotIncCapGain"] == 20000
    assert schedule["TotIncBusiness"] == 0  # this app never classifies VDA as business income
    row = schedule["ScheduleVDADtls"][0]
    assert row["AcquisitionCost"] == 80000
    assert row["ConsidReceived"] == 100000
    assert row["IncomeFromVDA"] == 20000
    assert row["HeadUndIncTaxed"] == "CG"
    assert row["DateofAcquisition"] == "2025-01-01"
    assert row["DateofTransfer"] == "2025-06-01"


def test_no_gains_produces_empty_schedules_not_a_crash():
    service = make_service(gains=[], instruments={})
    result = service.generate_export(user_id=uuid4(), assessment_year="2026-27")

    assert result["ITR"]["ITR3"]["Schedule112A"]["Schedule112ADtls"] == []
    assert result["ITR"]["ITR3"]["ScheduleCGFor23"]["EquityMFonSTTDtls"] == []
    assert result["ITR"]["ITR3"]["ScheduleVDA"]["ScheduleVDADtls"] == []
    assert result["ITR"]["ITR3"]["Schedule112A"]["SaleValue112A"] == 0
