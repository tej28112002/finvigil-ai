from decimal import Decimal
from typing import List
from datetime import datetime
from uuid import UUID

from app.models.holding_lot import HoldingLot
from app.repositories.holding_lot_repository import HoldingLotRepository


class HoldingLotService:
    def __init__(self, holding_repository: HoldingLotRepository):
        self.holding_repository = holding_repository

    def create_holding_lot(
        self,
        user_id: UUID,
        broker_connection_id: UUID,
        instrument_id: UUID,
        source_trade_id: UUID,
        quantity: Decimal,
        buy_price: Decimal,
        buy_date: datetime,
    ) -> HoldingLot:
        return self.holding_repository.create_lot(
            user_id=user_id,
            broker_connection_id=broker_connection_id,
            instrument_id=instrument_id,
            source_trade_id=source_trade_id,
            quantity_bought=quantity,
            remaining_quantity=quantity,
            buy_price=buy_price,
            buy_date=buy_date,
            status="open"
        )

    def get_open_lots(self, user_id: UUID, instrument_id: UUID) -> List[HoldingLot]:
        return self.holding_repository.get_open_lots(
            user_id=user_id,
            instrument_id=instrument_id
        )

    def reduce_lot_quantity(self, lot_id: UUID, new_quantity: Decimal) -> HoldingLot:
        lot = self.holding_repository.get_by_id(lot_id)
        if not lot:
            raise ValueError(f"HoldingLot with id {lot_id} not found.")

        if new_quantity == Decimal("0"):
            status = "closed"
        else:
            status = "partial"

        return self.holding_repository.update_remaining_quantity(
            lot=lot,
            remaining_quantity=new_quantity,
            status=status
        )

    def consume_lots_fifo(
        self,
        user_id: UUID,
        instrument_id: UUID,
        sell_quantity: Decimal,
        sell_price: Decimal,
        sell_date: datetime
    ) -> list[dict]:
        # Step 1 — Fetch open and partial lots (already ordered by buy_date asc)
        open_lots = self.holding_repository.get_open_lots(
            user_id=user_id,
            instrument_id=instrument_id
        )

        # Step 2 — Validate before touching anything
        if not open_lots:
            raise ValueError(
                "No open lots found for this instrument."
            )

        total_available = sum(
            Decimal(str(lot.quantity_remaining))
            for lot in open_lots
        )

        if sell_quantity > total_available:
            raise ValueError(
                f"Insufficient shares. "
                f"Tried to sell {sell_quantity} "
                f"but only {total_available} available."
            )

        # Step 3 — FIFO consumption loop
        remaining = sell_quantity
        consumption_breakdown = []

        for lot in open_lots:

            if remaining <= Decimal("0"):
                break

            lot_remaining = Decimal(str(lot.quantity_remaining))

            if remaining >= lot_remaining:
                consumed = lot_remaining
                new_qty = Decimal("0")
                new_status = "closed"
            else:
                consumed = remaining
                new_qty = lot_remaining - consumed
                new_status = "partial"

            self.holding_repository.update_remaining_quantity(
                lot=lot,
                remaining_quantity=new_qty,
                status=new_status
            )

            holding_days = (sell_date - lot.buy_date).days

            if holding_days > 365:
                gain_type = "LTCG"
            else:
                gain_type = "STCG"

            buy_price_decimal = Decimal(str(lot.buy_price))
            profit_loss = (sell_price - buy_price_decimal) * consumed

            consumption_breakdown.append({
                "lot_id": lot.id,
                "buy_date": lot.buy_date,
                "buy_price": buy_price_decimal,
                "quantity_consumed": consumed,
                "sell_price": sell_price,
                "sell_date": sell_date,
                "holding_days": holding_days,
                "gain_type": gain_type,
                "profit_loss": profit_loss
            })

            remaining = remaining - consumed

        return consumption_breakdown

    def get_lots_by_user(
        self,
        user_id: UUID
    ) -> list[HoldingLot]:
        return self.holding_repository.get_by_user(
            user_id=user_id
        )

    def get_lot_by_id(
        self,
        lot_id: UUID,
        user_id: UUID,
    ) -> HoldingLot | None:
        return self.holding_repository.get_by_id_and_user(
            lot_id=lot_id,
            user_id=user_id,
        )
