from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from app.core.tax_utils import get_ay_date_range
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.services.price_service import PriceService

ZERO = Decimal("0")
STCG_TAX_RATE = Decimal("0.20")
LTCG_TAX_RATE = Decimal("0.125")
LTCG_EXEMPTION = Decimal("125000")
LTCG_HOLDING_DAYS_THRESHOLD = 365  # matches holding_service.consume_lots_fifo exactly


class HarvestingService:
    """
    Tax-loss harvesting: surfaces OPEN holding lots currently sitting at an
    unrealized loss — positions that, if sold before March 31, "harvest"
    that loss to offset capital gains elsewhere and reduce tax liability.

    Computed on demand from holding_lots + live prices, same pattern as the
    crypto tax engine (no summary table — always reflects current state).
    """

    def __init__(
        self,
        holding_repository: HoldingLotRepository,
        realized_gain_repository: RealizedGainRepository,
        price_service: PriceService,
    ):
        self.holding_repository = holding_repository
        self.realized_gain_repository = realized_gain_repository
        self.price_service = price_service

    def _existing_ltcg_gains(self, user_id: UUID, assessment_year: str) -> Decimal:
        """
        Sum of the user's ALREADY-REALIZED LTCG gains for this AY (equity
        only). Used to answer "would harvesting more LTCG loss actually
        save tax this year": the ₹1,25,000 exemption applies to the whole
        year's net LTCG, not per-transaction — if existing gains are
        already at or below the exemption, there is no taxable LTCG for a
        new loss to offset, so the marginal saving is honestly ₹0, not
        12.5% of the loss. This checks the CURRENT realized position only
        (not cumulative across the candidate list being evaluated) — a
        documented simplification, same spirit as the crypto TDS
        per-transaction-threshold simplification elsewhere in this project.
        """
        start, end = get_ay_date_range(assessment_year)
        gains = self.realized_gain_repository.get_by_user_income_type_and_date_range(
            user_id=user_id,
            income_type="equity_capital_gains",
            start=start,
            end=end,
        )
        return sum(
            (Decimal(str(g.profit_loss)) for g in gains if g.gain_type == "LTCG"),
            ZERO,
        )

    def get_harvest_candidates(
        self,
        user_id: UUID,
        assessment_year: str,
    ) -> list[dict]:
        lots = self.holding_repository.get_active_lots_by_user(user_id=user_id)
        if not lots:
            return []

        symbols = list({lot.instrument.symbol for lot in lots})
        price_data = self.price_service.get_prices(user_id=user_id, symbols=symbols)

        # Computed once, not per-candidate — this only depends on the
        # user's already-realized position, not on which lot we're
        # evaluating, so doing it per-candidate would be a redundant query
        # per lot (the exact N+1 shape found and fixed elsewhere this
        # project — see project-context.md.txt Section 25).
        existing_ltcg_gains = self._existing_ltcg_gains(user_id, assessment_year)
        ltcg_has_taxable_base = existing_ltcg_gains > LTCG_EXEMPTION

        now = datetime.now(timezone.utc)
        candidates: list[dict] = []

        for lot in lots:
            quantity = Decimal(str(lot.quantity_remaining))
            buy_price = Decimal(str(lot.buy_price))
            symbol = lot.instrument.symbol

            quote = price_data.get(symbol)
            if quote and quote.get("last_price") is not None:
                current_price = quote["last_price"]
                is_price_estimate = False
            else:
                # No live price available (no active broker token, or the
                # symbol wasn't returned) — fall back to cost basis,
                # clearly labeled. A cost-basis fallback can never itself
                # register as a loss (current_price - buy_price == 0), so
                # this lot simply won't appear as a candidate unless a real
                # live price is available and below cost — honest, not a
                # bug: we don't fabricate a loss we can't observe.
                current_price = buy_price
                is_price_estimate = True

            unrealized_loss = (current_price - buy_price) * quantity
            if unrealized_loss >= ZERO:
                continue  # only losses are harvest candidates

            holding_period_days = (now - lot.buy_date).days
            gain_type = (
                "LTCG" if holding_period_days > LTCG_HOLDING_DAYS_THRESHOLD else "STCG"
            )

            loss_magnitude = -unrealized_loss  # positive
            if gain_type == "STCG":
                estimated_tax_saving = loss_magnitude * STCG_TAX_RATE
            else:
                estimated_tax_saving = (
                    loss_magnitude * LTCG_TAX_RATE if ltcg_has_taxable_base else ZERO
                )

            candidates.append(
                {
                    "lot_id": lot.id,
                    "instrument_id": lot.instrument_id,
                    "symbol": symbol,
                    "quantity": quantity,
                    "buy_price": buy_price,
                    "buy_date": lot.buy_date,
                    "current_value": current_price * quantity,
                    "is_price_estimate": is_price_estimate,
                    "unrealized_loss": unrealized_loss,
                    "holding_period_days": holding_period_days,
                    "gain_type": gain_type,
                    "estimated_tax_saving": estimated_tax_saving,
                }
            )

        # Biggest tax saving first — the frontend's requested sort order.
        candidates.sort(key=lambda c: c["estimated_tax_saving"], reverse=True)
        return candidates

    def get_harvest_summary(
        self,
        user_id: UUID,
        assessment_year: str,
    ) -> dict:
        candidates = self.get_harvest_candidates(user_id, assessment_year)

        total_harvestable_loss = sum(
            (c["unrealized_loss"] for c in candidates), ZERO
        )  # signed negative, matching every other P&L figure in this app
        total_estimated_tax_saving = sum(
            (c["estimated_tax_saving"] for c in candidates), ZERO
        )

        _, ay_end = get_ay_date_range(assessment_year)
        march_31 = ay_end - timedelta(days=1)
        days_until_march_31 = max(
            0, (march_31.date() - datetime.now(timezone.utc).date()).days
        )

        return {
            "assessment_year": assessment_year,
            "total_harvestable_loss": total_harvestable_loss,
            "total_estimated_tax_saving": total_estimated_tax_saving,
            "candidate_count": len(candidates),
            "days_until_march_31": days_until_march_31,
        }
