from decimal import Decimal
from uuid import UUID

from app.repositories.holding_lot_repository import HoldingLotRepository


class PortfolioService:
    def __init__(
        self,
        holding_repository: HoldingLotRepository
    ):
        self.holding_repository = holding_repository

    def get_portfolio_summary(
        self,
        user_id: UUID
    ) -> list[dict]:
        active_lots = self.holding_repository.get_active_lots_by_user(
            user_id=user_id
        )

        grouped_lots = {}

        for lot in active_lots:
            qty = Decimal(str(lot.quantity_remaining))
            price = Decimal(str(lot.buy_price))
            invested = qty * price

            if lot.instrument_id not in grouped_lots:
                grouped_lots[lot.instrument_id] = {
                    "instrument_id": lot.instrument_id,
                    "symbol": lot.instrument.symbol,
                    "name": lot.instrument.name,
                    "instrument_type": lot.instrument.instrument_type,
                    "isin": lot.instrument.isin,
                    "total_quantity": Decimal("0"),
                    "total_invested": Decimal("0"),
                    "lot_count": 0,
                    "earliest_buy_date": lot.buy_date,
                }

            entry = grouped_lots[lot.instrument_id]
            entry["total_quantity"] += qty
            entry["total_invested"] += invested
            entry["lot_count"] += 1

            if lot.buy_date < entry["earliest_buy_date"]:
                entry["earliest_buy_date"] = lot.buy_date

        portfolio_summary = []

        for entry in grouped_lots.values():
            average_buy_price = (
                entry["total_invested"] / entry["total_quantity"]
                if entry["total_quantity"] > Decimal("0")
                else Decimal("0")
            )

            portfolio_summary.append({
                "instrument_id": entry["instrument_id"],
                "symbol": entry["symbol"],
                "name": entry["name"],
                "instrument_type": entry["instrument_type"],
                "isin": entry["isin"],
                "total_quantity": entry["total_quantity"],
                "total_invested": entry["total_invested"],
                "average_buy_price": average_buy_price,
                "lot_count": entry["lot_count"],
                "earliest_buy_date": entry["earliest_buy_date"],
            })

        return portfolio_summary
