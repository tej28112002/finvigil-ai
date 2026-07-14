from uuid import UUID

from app.models.realized_gain import RealizedGain
from app.repositories.realized_gain_repository import RealizedGainRepository


class RealizedGainService:
    def __init__(
        self,
        realized_gain_repository: RealizedGainRepository
    ):
        self.realized_gain_repository = realized_gain_repository

    def get_gains_by_user(
        self,
        user_id: UUID
    ) -> list[RealizedGain]:
        return self.realized_gain_repository.get_by_user(
            user_id=user_id
        )

    def get_gains_by_instrument(
        self,
        user_id: UUID,
        instrument_id: UUID
    ) -> list[RealizedGain]:
        return self.realized_gain_repository.get_by_instrument(
            user_id=user_id,
            instrument_id=instrument_id
        )

    def get_gains_by_sell_trade(
        self,
        sell_trade_id: UUID,
        user_id: UUID,
    ) -> list[RealizedGain]:
        return self.realized_gain_repository.get_by_sell_trade_and_user(
            sell_trade_id=sell_trade_id,
            user_id=user_id,
        )
