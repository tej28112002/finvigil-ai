from decimal import Decimal
from datetime import datetime
from uuid import UUID

from app.models.tax_summary import TaxSummary
from app.repositories.tax_summary_repository import TaxSummaryRepository
from app.repositories.realized_gain_repository import RealizedGainRepository


class TaxEngineService:
    def __init__(
        self,
        tax_summary_repository: TaxSummaryRepository,
        realized_gain_repository: RealizedGainRepository,
    ):
        self.tax_summary_repository = tax_summary_repository
        self.realized_gain_repository = realized_gain_repository

    def get_assessment_year(self, sell_date: datetime) -> str:
        if sell_date.month >= 4:
            fy_start_year = sell_date.year
        else:
            fy_start_year = sell_date.year - 1

        ay_start_year = fy_start_year + 1
        ay_end_year = ay_start_year + 1

        return f"{ay_start_year}-{str(ay_end_year)[2:]}"

    def calculate_tax_summary(
        self,
        user_id: UUID,
        assessment_year: str,
    ) -> TaxSummary:
        # Step 1 — Fetch all realized gains for user
        all_gains = self.realized_gain_repository.get_by_user(
            user_id=user_id
        )

        # Step 2 — Filter gains belonging to this assessment_year
        filtered_gains = [
            gain for gain in all_gains
            if self.get_assessment_year(gain.sell_date) == assessment_year
        ]

        # Step 3 — Sum by gain_type using Decimal
        total_stcg = Decimal("0")
        total_ltcg = Decimal("0")

        for gain in filtered_gains:
            profit = Decimal(str(gain.profit_loss))
            if gain.gain_type == "STCG":
                total_stcg += profit
            elif gain.gain_type == "LTCG":
                total_ltcg += profit

        # Step 4 — Define tax rates and exemption
        stcg_tax_rate = Decimal("0.20")
        ltcg_tax_rate = Decimal("0.125")
        ltcg_exemption = Decimal("125000")

        # Step 5 — Calculate taxable amounts
        taxable_stcg = max(Decimal("0"), total_stcg)
        taxable_ltcg = max(Decimal("0"), total_ltcg - ltcg_exemption)

        # Step 6 — Calculate tax amounts
        stcg_tax = taxable_stcg * stcg_tax_rate
        ltcg_tax = taxable_ltcg * ltcg_tax_rate
        total_tax_liability = stcg_tax + ltcg_tax

        # Step 7 — Save via upsert and return
        return self.tax_summary_repository.upsert_tax_summary(
            user_id=user_id,
            assessment_year=assessment_year,
            total_stcg_gains=total_stcg,
            total_ltcg_gains=total_ltcg,
            stcg_tax_rate=stcg_tax_rate,
            ltcg_tax_rate=ltcg_tax_rate,
            ltcg_exemption=ltcg_exemption,
            taxable_stcg=taxable_stcg,
            taxable_ltcg=taxable_ltcg,
            stcg_tax=stcg_tax,
            ltcg_tax=ltcg_tax,
            total_tax_liability=total_tax_liability,
        )

    def get_tax_summary(
        self,
        user_id: UUID,
        assessment_year: str,
    ) -> TaxSummary | None:
        return self.tax_summary_repository.get_by_user_and_year(
            user_id=user_id,
            assessment_year=assessment_year,
        )

    def get_all_tax_summaries(
        self,
        user_id: UUID,
    ) -> list[TaxSummary]:
        return self.tax_summary_repository.get_all_by_user(
            user_id=user_id,
        )
