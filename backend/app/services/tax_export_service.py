from decimal import Decimal
from uuid import UUID

from app.core.tax_utils import get_assessment_year
from app.models.ca_export_job import CaExportJob
from app.repositories.tax_summary_repository import TaxSummaryRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.ca_export_job_repository import CaExportJobRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.schemas.tax_export import (
    TransactionDetail,
    CapitalGainsSummary,
    CapitalGainsExportResponse,
)


class TaxExportService:
    def __init__(
        self,
        tax_summary_repository: TaxSummaryRepository,
        realized_gain_repository: RealizedGainRepository,
        ca_export_job_repository: CaExportJobRepository,
        instrument_repository: InstrumentRepository,
    ):
        self.tax_summary_repository = tax_summary_repository
        self.realized_gain_repository = realized_gain_repository
        self.ca_export_job_repository = ca_export_job_repository
        self.instrument_repository = instrument_repository

    def generate_export(
        self,
        user_id: UUID,
        assessment_year: str,
    ) -> CapitalGainsExportResponse:
        tax_summary = self.tax_summary_repository.get_by_user_and_year(
            user_id=user_id,
            assessment_year=assessment_year,
        )
        if not tax_summary:
            raise ValueError(
                f"No tax summary found for assessment year {assessment_year}. "
                f"Call POST /tax/calculate first to generate one."
            )

        # EQUITY only — crypto VDA gains have their own export/engine and must
        # not appear in the capital-gains export.
        all_gains = self.realized_gain_repository.get_by_user_and_income_type(
            user_id=user_id,
            income_type="equity_capital_gains",
        )
        filtered_gains = [
            gain for gain in all_gains
            if get_assessment_year(gain.sell_date) == assessment_year
        ]

        unique_instrument_ids = list({gain.instrument_id for gain in filtered_gains})
        instruments = {}
        for instrument_id in unique_instrument_ids:
            instrument = self.instrument_repository.get_by_id(instrument_id)
            if instrument:
                instruments[instrument_id] = instrument
        # NOTE: This performs one DB query per unique instrument.
        # Acceptable for current data sizes. Replace with a bulk
        # get_by_ids() method in a future performance optimisation pass.

        transactions = []
        for gain in filtered_gains:
            instrument = instruments.get(gain.instrument_id)
            transactions.append(TransactionDetail(
                symbol=instrument.symbol if instrument else "UNKNOWN",
                isin=instrument.isin if instrument else None,
                quantity_sold=Decimal(str(gain.quantity_sold)),
                buy_date=gain.buy_date,
                sell_date=gain.sell_date,
                buy_price=Decimal(str(gain.buy_price)),
                sell_price=Decimal(str(gain.sell_price)),
                holding_days=gain.holding_days,
                gain_type=gain.gain_type,
                profit_loss=Decimal(str(gain.profit_loss)),
            ))

        transactions.sort(key=lambda t: (t.sell_date, t.buy_date))

        summary = CapitalGainsSummary(
            total_stcg_gains=Decimal(str(tax_summary.total_stcg_gains)),
            total_ltcg_gains=Decimal(str(tax_summary.total_ltcg_gains)),
            taxable_stcg=Decimal(str(tax_summary.taxable_stcg)),
            taxable_ltcg=Decimal(str(tax_summary.taxable_ltcg)),
            stcg_tax_estimate=Decimal(str(tax_summary.stcg_tax)),
            ltcg_tax_estimate=Decimal(str(tax_summary.ltcg_tax)),
            total_tax_estimate=Decimal(str(tax_summary.total_tax_liability)),
            ltcg_exemption_applied=Decimal(str(tax_summary.ltcg_exemption)),
        )

        export_job: CaExportJob = self.ca_export_job_repository.create_export_job(
            user_id=user_id,
            assessment_year=assessment_year,
            export_type="capital_gains_json",
            status="completed",
        )

        return CapitalGainsExportResponse(
            export_id=export_job.id,
            export_type="capital_gains_json",
            assessment_year=assessment_year,
            generated_at=export_job.created_at,
            user_id=user_id,
            disclaimer=(
                "This is a CA-assistance export only, not a government-uploadable file. "
                "Figures represent capital gains from broker data in FinVigil. "
                "Verify all figures against your broker statements and AIS before filing. "
                "Does NOT include cess, surcharge, or tax on other income sources. "
                "Consult your CA for final ITR preparation."
            ),
            summary=summary,
            transactions=transactions,
        )