from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.core.tax_utils import get_ay_date_range
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.itr_schema_repository import ItrSchemaRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.tax_summary_repository import TaxSummaryRepository

ZERO = Decimal("0")

_DISCLAIMER = (
    "Contains Schedule 112A (LTCG equity), Schedule CG Sec 111A (STCG "
    "equity), and Schedule VDA (crypto) only. Personal details, salary, "
    "house property, TDS schedules, and final tax computation must be "
    "added by the user or CA before filing. Grandfathering (31-Jan-2018 "
    "fair market value) is not applied — fair market value is reported "
    "equal to acquisition cost, which cannot understate LTCG relative to "
    "the true grandfathered figure. Transfer/improvement expenses and "
    "Section 94(7)/94(8) bonus-stripping losses are not tracked and are "
    "reported as zero. Not a government-uploadable file — verify every "
    "figure against your broker statements and AIS before filing."
)


class ItrSchemaNotFoundError(ValueError):
    """Raised when no schema mapping exists (or none is active) for the
    requested AY — a distinct type from the plain ValueError used for
    tax-summary-missing, so the API layer can map each to a different
    HTTP status without string-sniffing the message."""


def _money(value) -> int:
    """Exact Decimal math internally; converts to int ONLY at the final
    JSON boundary, per this project's money-handling rule. round() on a
    Decimal with no ndigits returns a Python int directly (banker's
    rounding), so the outer int() is a no-op safety net, not a truncation."""
    return int(round(Decimal(str(value))))


class ITR3ExportService:
    """
    FR-AIS-05 — schema-driven ITR-3 partial-return export. Every CBDT field
    name used below comes from ItrSchemaMapping.mapping_json (looked up by
    AY), never hardcoded — a new assessment year's schema is added via the
    Admin Panel (POST /admin/itr-schemas) with no code change or deploy.
    """

    def __init__(
        self,
        itr_schema_repository: ItrSchemaRepository,
        realized_gain_repository: RealizedGainRepository,
        tax_summary_repository: TaxSummaryRepository,
        instrument_repository: InstrumentRepository,
    ):
        self.itr_schema_repository = itr_schema_repository
        self.realized_gain_repository = realized_gain_repository
        self.tax_summary_repository = tax_summary_repository
        self.instrument_repository = instrument_repository

    def generate_export(self, user_id: UUID, assessment_year: str) -> dict:
        # STEP A — load the mapping for this AY. An inactive mapping is
        # treated the same as no mapping — a broken schema an admin has
        # deactivated must not still be reachable by users.
        mapping_record = self.itr_schema_repository.get_by_ay(assessment_year)
        if not mapping_record or not mapping_record.is_active:
            raise ItrSchemaNotFoundError(
                f"ITR-3 export not supported for AY {assessment_year}. "
                f"Upload the schema mapping via Admin Panel first."
            )
        mapping = mapping_record.mapping_json

        # STEP B — fetch data
        tax_summary = self.tax_summary_repository.get_by_user_and_year(
            user_id=user_id, assessment_year=assessment_year
        )
        if not tax_summary:
            raise ValueError(
                f"No tax summary found for AY {assessment_year}. "
                f"Run POST /tax/calculate first."
            )

        ay_start, ay_end = get_ay_date_range(assessment_year)

        equity_gains = self.realized_gain_repository.get_by_user_income_type_and_date_range(
            user_id=user_id,
            income_type="equity_capital_gains",
            start=ay_start,
            end=ay_end,
        )
        crypto_gains = self.realized_gain_repository.get_by_user_income_type_and_date_range(
            user_id=user_id,
            income_type="crypto_vda",
            start=ay_start,
            end=ay_end,
        )
        all_gains = equity_gains + crypto_gains

        instrument_ids = {g.instrument_id for g in all_gains}
        instruments = {}
        for instrument_id in instrument_ids:
            instrument = self.instrument_repository.get_by_id(instrument_id)
            if instrument:
                instruments[instrument_id] = instrument

        # STEP C — separate by type
        ltcg_equity = [
            g for g in equity_gains
            if g.gain_type == "LTCG"
            and instruments.get(g.instrument_id)
            and instruments[g.instrument_id].instrument_type == "equity"
        ]
        stcg_equity = [
            g for g in equity_gains
            if g.gain_type == "STCG"
            and instruments.get(g.instrument_id)
            and instruments[g.instrument_id].instrument_type == "equity"
        ]
        crypto = [
            g for g in crypto_gains
            if instruments.get(g.instrument_id)
            and instruments[g.instrument_id].instrument_type == "crypto"
        ]

        schedule_112a = self._build_schedule_112a(mapping, ltcg_equity, instruments)
        schedule_cg = self._build_schedule_cg_for_23(mapping, stcg_equity)
        schedule_vda = self._build_schedule_vda(mapping, crypto)

        return {
            "partial_return": True,
            "schema_version": (
                f"ITR-3-AY-{assessment_year}-V{mapping['schema_version']}"
            ),
            "generated_by": "FinVigil AI",
            "assessment_year": assessment_year,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": _DISCLAIMER,
            "ITR": {
                "ITR3": {
                    "Schedule112A": schedule_112a,
                    "ScheduleCGFor23": schedule_cg,
                    "ScheduleVDA": schedule_vda,
                }
            },
        }

    # ------------------------------------------------------------------
    # Schedule builders — every emitted field name is read from `mapping`,
    # never hardcoded, so a new AY's CBDT field names only need a new
    # mapping_json row, not a code change.
    # ------------------------------------------------------------------

    @staticmethod
    def _build_schedule_112a(mapping: dict, gains: list, instruments: dict) -> dict:
        cfg = mapping["ltcg_equity"]
        tf = cfg["transaction_fields"]
        sf = cfg["summary_fields"]
        constants = mapping["constants"]
        exemption_limit = Decimal(str(mapping["ltcg_exemption_limit"]))

        transactions = []
        total_sale_value = ZERO
        total_cost = ZERO
        total_acquisition_cost = ZERO
        total_ltcg_before_exemption = ZERO
        total_fmv = ZERO

        for g in gains:
            instrument = instruments.get(g.instrument_id)
            isin = (
                instrument.isin if instrument and instrument.isin
                else constants["isin_not_available"]
            )
            quantity = Decimal(str(g.quantity_sold))
            sell_price = Decimal(str(g.sell_price))
            buy_price = Decimal(str(g.buy_price))

            sale_value = sell_price * quantity
            cost = buy_price * quantity
            # No 31-Jan-2018 fair-market-value tracking (grandfathering) —
            # FMV is reported equal to acquisition cost, i.e. no
            # grandfathering benefit is claimed. Conservative: this can
            # only overstate LTCG, never understate it. See _DISCLAIMER.
            fmv_per_unit = buy_price
            total_fmv_txn = cost
            ltcg_before_exemption = sale_value - cost

            total_sale_value += sale_value
            total_cost += cost
            total_acquisition_cost += cost
            total_ltcg_before_exemption += ltcg_before_exemption
            total_fmv += total_fmv_txn

            transactions.append({
                tf["share_on_or_before"]: constants["share_on_or_before_flag_modern"],
                tf["isin"]: isin,
                tf["symbol"]: instrument.symbol if instrument else "UNKNOWN",
                tf["quantity"]: _money(quantity),
                tf["sale_price_per_unit"]: _money(sell_price),
                tf["total_sale_value"]: _money(sale_value),
                tf["cost_without_indexation"]: _money(cost),
                tf["acquisition_cost"]: _money(cost),
                tf["ltcg_before_exemption"]: _money(ltcg_before_exemption),
                tf["fair_market_value_per_unit"]: _money(fmv_per_unit),
                tf["total_fair_market_value"]: _money(total_fmv_txn),
                tf["transfer_expenses"]: 0,
                tf["total_deductions"]: 0,
                tf["balance"]: _money(ltcg_before_exemption),
            })

        # The Rs. 1,25,000 LTCG exemption applies once to the YEAR'S total,
        # not per transaction.
        balance_after_exemption = max(
            ZERO, total_ltcg_before_exemption - exemption_limit
        )

        return {
            cfg["transaction_array"]: transactions,
            sf["total_sale_value"]: _money(total_sale_value),
            sf["total_cost"]: _money(total_cost),
            sf["total_acquisition_cost"]: _money(total_acquisition_cost),
            sf["total_ltcg_before_exemption"]: _money(total_ltcg_before_exemption),
            sf["fair_market_value"]: _money(total_fmv),
            sf["transfer_expenses"]: 0,
            sf["deductions"]: 0,
            sf["balance_after_exemption"]: _money(balance_after_exemption),
        }

    @staticmethod
    def _build_schedule_cg_for_23(mapping: dict, gains: list) -> dict:
        cfg = mapping["stcg_equity_111a"]
        f = cfg["fields"]

        full_consideration = ZERO
        acquisition_cost = ZERO
        for g in gains:
            quantity = Decimal(str(g.quantity_sold))
            full_consideration += Decimal(str(g.sell_price)) * quantity
            acquisition_cost += Decimal(str(g.buy_price)) * quantity

        improvement_cost = ZERO
        transfer_expenses = ZERO
        deduct_sec48 = acquisition_cost + improvement_cost + transfer_expenses
        total_deduction = deduct_sec48
        balance_cg = full_consideration - total_deduction
        loss_sec94 = ZERO  # not tracked — see _DISCLAIMER
        capital_gain = balance_cg - loss_sec94

        row = {
            f["section_code"]: cfg["section_code"],
            f["full_consideration"]: _money(full_consideration),
            f["deduct_sec48"]: _money(deduct_sec48),
            f["acquisition_cost"]: _money(acquisition_cost),
            f["improvement_cost"]: _money(improvement_cost),
            f["transfer_expenses"]: _money(transfer_expenses),
            f["total_deduction"]: _money(total_deduction),
            f["balance_cg"]: _money(balance_cg),
            f["loss_sec94"]: _money(loss_sec94),
            f["capital_gain"]: _money(capital_gain),
        }

        return {
            f["details_key"]: [row] if gains else [],
            f["total_stcg"]: _money(capital_gain) if gains else 0,
        }

    @staticmethod
    def _build_schedule_vda(mapping: dict, gains: list) -> dict:
        cfg = mapping["vda_crypto"]
        tf = cfg["transaction_fields"]
        sf = cfg["summary_fields"]
        head = mapping["constants"]["vda_head_under_income"]

        transactions = []
        total_capital_gain = ZERO

        for g in gains:
            quantity = Decimal(str(g.quantity_sold))
            acquisition_cost = Decimal(str(g.buy_price)) * quantity
            consideration = Decimal(str(g.sell_price)) * quantity
            income = Decimal(str(g.profit_loss))
            total_capital_gain += income

            transactions.append({
                tf["date_of_acquisition"]: g.buy_date.date().isoformat(),
                tf["date_of_transfer"]: g.sell_date.date().isoformat(),
                tf["head_under_income"]: head,
                tf["acquisition_cost"]: _money(acquisition_cost),
                tf["consideration_received"]: _money(consideration),
                tf["income_from_vda"]: _money(income),
            })

        return {
            cfg["transaction_array"]: transactions,
            sf["total_business_income"]: 0,  # this app never classifies VDA as business income
            sf["total_capital_gain"]: _money(total_capital_gain),
        }
