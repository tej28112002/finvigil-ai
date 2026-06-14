from decimal import Decimal
from uuid import UUID

from app.models.dashboard_projection import DashboardProjection
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.holding_lot_repository import HoldingLotRepository


class DashboardService:
    def __init__(
        self,
        dashboard_repository: DashboardRepository,
        holding_repository: HoldingLotRepository
    ):
        self.dashboard_repository = dashboard_repository
        self.holding_repository = holding_repository

    def calculate_and_update_projection(
        self,
        user_id: UUID
    ) -> DashboardProjection:
        all_lots = self.holding_repository.get_by_user(
            user_id=user_id
        )

        active_lots = [
            lot for lot in all_lots
            if lot.status in ["open", "partial"]
        ]

        total_equity_value = Decimal("0")
        total_crypto_value = Decimal("0")

        for lot in active_lots:
            # TODO: Replace lot.buy_price with
            # live market price when broker
            # price feed is connected (Phase 4.6+)
            current_price = Decimal(str(lot.buy_price))
            value = (
                Decimal(str(lot.quantity_remaining))
                * current_price
            )

            # TODO: Once Instrument relationship
            # is loaded, split by
            # instrument.instrument_type ==
            # "crypto" vs others (Phase 5+)
            total_equity_value += value

        day_pnl = Decimal("0")
        # TODO: Calculate from live price -
        # previous close price (Phase 4.6+)

        unrealized_pnl = Decimal("0")
        # TODO: Calculate from
        # (live_price - buy_price) * quantity_remaining
        # (Phase 4.6+)

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
