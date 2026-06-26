from decimal import Decimal
from datetime import datetime
from uuid import UUID

from app.models.corporate_action_adjustment import CorporateActionAdjustment
from app.repositories.corporate_action_repository import CorporateActionRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.schemas.corporate_action import CorporateActionAppliedResponse


class CorporateActionService:
    def __init__(
        self,
        corporate_action_repository: CorporateActionRepository,
        holding_lot_repository: HoldingLotRepository,
    ):
        self.corporate_action_repository = corporate_action_repository
        self.holding_lot_repository = holding_lot_repository

    def apply_corporate_action(
        self,
        user_id: UUID,
        instrument_id: UUID,
        action_type: str,
        ratio: Decimal,
        applied_at: datetime,
    ) -> CorporateActionAppliedResponse:
        allowed = ["stock_split", "bonus_issue"]
        if action_type not in allowed:
            raise ValueError(
                f"Invalid action type: {action_type}. "
                f"Must be one of {allowed}."
            )

        if ratio <= Decimal("1"):
            raise ValueError(
                f"Ratio must be greater than 1. Got {ratio}."
            )

        existing = self.corporate_action_repository.get_duplicate(
            user_id=user_id,
            instrument_id=instrument_id,
            action_type=action_type,
            applied_at=applied_at,
        )
        if existing:
            raise ValueError(
                f"A {action_type} has already been applied for this "
                f"instrument on {applied_at}. Cannot apply twice."
            )

        affected_lots = self.holding_lot_repository.get_open_lots_before_date(
            user_id=user_id,
            instrument_id=instrument_id,
            before_date=applied_at,
        )

        lots_adjusted = 0
        for lot in affected_lots:
            old_qty_bought = Decimal(str(lot.quantity_bought))
            old_qty_remaining = Decimal(str(lot.quantity_remaining))
            old_price = Decimal(str(lot.buy_price))

            new_qty_bought = old_qty_bought * ratio
            new_qty_remaining = old_qty_remaining * ratio
            new_price = old_price / ratio

            self.holding_lot_repository.apply_corporate_action_to_lot(
                lot=lot,
                new_quantity_bought=new_qty_bought,
                new_quantity_remaining=new_qty_remaining,
                new_buy_price=new_price,
            )
            lots_adjusted += 1

        adjustment = self.corporate_action_repository.create_adjustment(
            user_id=user_id,
            instrument_id=instrument_id,
            action_type=action_type,
            ratio=ratio,
            applied_at=applied_at,
        )

        return CorporateActionAppliedResponse(
            id=adjustment.id,
            user_id=adjustment.user_id,
            instrument_id=adjustment.instrument_id,
            action_type=adjustment.action_type,
            ratio=Decimal(str(adjustment.ratio)),
            applied_at=adjustment.applied_at,
            lots_adjusted=lots_adjusted,
            created_at=adjustment.created_at,
        )

    def get_adjustments_by_user(
        self,
        user_id: UUID,
    ) -> list[CorporateActionAdjustment]:
        return self.corporate_action_repository.get_by_user(
            user_id=user_id
        )
