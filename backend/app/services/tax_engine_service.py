from decimal import Decimal
from uuid import UUID

from app.core.tax_utils import get_ay_date_range
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

    def calculate_tax_summary(
        self,
        user_id: UUID,
        assessment_year: str,
    ) -> TaxSummary:
        # Step 1 — Fetch EQUITY realized gains for this AY only, at the SQL
        # level. Crypto VDA gains (income_type='crypto_vda') are taxed by
        # the crypto engine at a flat 30% with no set-off and must never
        # enter the STCG/LTCG computation. Previously fetched the user's
        # entire equity gain history and filtered by AY in Python.
        start, end = get_ay_date_range(assessment_year)
        filtered_gains = self.realized_gain_repository.get_by_user_income_type_and_date_range(
            user_id=user_id,
            income_type="equity_capital_gains",
            start=start,
            end=end,
        )

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

        # STEP 5 — Net STCG/LTCG against each other (set-off),
        # then apply LTCG exemption
        if total_stcg < Decimal("0") and total_ltcg > Decimal("0"):
            # STCG loss offsets LTCG gain
            net_ltcg = total_ltcg + total_stcg
            net_stcg = Decimal("0")
        elif total_ltcg < Decimal("0") and total_stcg > Decimal("0"):
            # LTCG loss offsets STCG gain
            net_stcg = total_stcg + total_ltcg
            net_ltcg = Decimal("0")
        else:
            # Same sign or one/both zero — no offsetting applicable
            net_stcg = total_stcg
            net_ltcg = total_ltcg

        taxable_stcg = max(Decimal("0"), net_stcg)
        taxable_ltcg = max(Decimal("0"), net_ltcg - ltcg_exemption)

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
