from decimal import Decimal
from uuid import UUID

from app.core.tax_utils import get_assessment_year
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.tds_ledger_repository import TdsLedgerRepository

ZERO = Decimal("0")
VDA_TAX_RATE = Decimal("0.30")
INCOME_TYPE_CRYPTO = "crypto_vda"


class CryptoTaxService:
    """
    Crypto / VDA tax engine (Section 115BBH). Flat 30% on gains, NO set-off:
    a loss on one VDA cannot offset a gain on another, cannot offset any other
    income, and cannot be carried forward. So taxable income = sum of POSITIVE
    per-transaction gains; losses are disclosed but not deductible. 1% TDS
    already deducted at source is a credit against the final tax.

    Computed on demand (no summary table).
    """

    def __init__(
        self,
        realized_gain_repository: RealizedGainRepository,
        tds_ledger_repository: TdsLedgerRepository,
    ):
        self.realized_gain_repository = realized_gain_repository
        self.tds_ledger_repository = tds_ledger_repository

    def calculate_crypto_tax(
        self,
        user_id: UUID,
        assessment_year: str,
    ) -> dict:
        gains = self.realized_gain_repository.get_by_user_and_income_type(
            user_id=user_id,
            income_type=INCOME_TYPE_CRYPTO,
        )
        gains_in_ay = [
            g for g in gains
            if get_assessment_year(g.sell_date) == assessment_year
        ]

        total_vda_gains = ZERO
        total_vda_losses = ZERO
        for g in gains_in_ay:
            pl = Decimal(str(g.profit_loss))
            if pl > ZERO:
                total_vda_gains += pl
            elif pl < ZERO:
                total_vda_losses += pl

        # No set-off: only positive gains are taxable; losses excluded.
        taxable_vda_income = total_vda_gains
        vda_tax = taxable_vda_income * VDA_TAX_RATE

        # TDS already deducted this AY (credit against tax).
        tds_entries = self.tds_ledger_repository.get_by_user(user_id=user_id)
        total_tds_paid = ZERO
        for entry in tds_entries:
            if get_assessment_year(entry.timestamp) == assessment_year:
                total_tds_paid += Decimal(str(entry.amount))

        net_tax_payable = vda_tax - total_tds_paid

        return {
            "assessment_year": assessment_year,
            "transaction_count": len(gains_in_ay),
            "total_vda_gains": total_vda_gains,
            "total_vda_losses": total_vda_losses,
            "taxable_vda_income": taxable_vda_income,
            "vda_tax_rate": VDA_TAX_RATE,
            "vda_tax": vda_tax,
            "total_tds_paid": total_tds_paid,
            "net_tax_payable": net_tax_payable,
        }
