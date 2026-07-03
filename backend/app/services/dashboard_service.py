from decimal import Decimal
from uuid import UUID

from app.models.dashboard_projection import DashboardProjection
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.services.price_service import PriceService


class DashboardService:
    def __init__(
        self,
        dashboard_repository: DashboardRepository,
        holding_repository: HoldingLotRepository,
        price_service: PriceService,
    ):
        self.dashboard_repository = dashboard_repository
        self.holding_repository = holding_repository
        self.price_service = price_service

    def calculate_and_update_projection(
        self,
        user_id: UUID
    ) -> DashboardProjection:
        active_lots = self.holding_repository.get_active_lots_by_user(
            user_id=user_id
        )

        total_equity_value = Decimal("0")
        total_crypto_value = Decimal("0")
        day_pnl = Decimal("0")
        unrealized_pnl = Decimal("0")

        if active_lots:
            symbols = list({lot.instrument.symbol for lot in active_lots})
            price_data = self.price_service.get_prices(
                user_id=user_id,
                symbols=symbols,
            )

            for lot in active_lots:
                symbol = lot.instrument.symbol
                quote = price_data.get(symbol, {})

                last_price = quote.get("last_price") or Decimal(str(lot.buy_price))
                prev_close = quote.get("prev_close") or last_price

                quantity = Decimal(str(lot.quantity_remaining))
                buy_price = Decimal(str(lot.buy_price))

                value = quantity * last_price
                day_pnl += (last_price - prev_close) * quantity
                unrealized_pnl += (last_price - buy_price) * quantity

                if lot.instrument.instrument_type == "crypto":
                    total_crypto_value += value
                else:
                    total_equity_value += value

        return self.dashboard_repository.upsert_projection(
            user_id=user_id,
            total_equity_value=total_equity_value,
            total_crypto_value=total_crypto_value,
            day_pnl=day_pnl,
            unrealized_pnl=unrealized_pnl
        )

    def get_projection(
        self,
        user_id: UUID
    ) -> DashboardProjection | None:
        return self.dashboard_repository.get_by_user(
            user_id=user_id
        )
