from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID

from app.models.trade import Trade
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.trade_repository import TradeRepository
from app.services.holding_service import HoldingLotService


def _to_utc(dt: datetime) -> datetime:
    """
    Normalize a naive datetime to UTC. The DB stores TIMESTAMPTZ, so a
    holding_lot's buy_date read back is always tz-aware; a naive
    execution_time here would fail to subtract during FIFO (see
    holding_service.consume_lots_fifo). Same fix as crypto_service.py.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class TradeService:
    def __init__(
        self,
        trade_repository: TradeRepository,
        holding_service: HoldingLotService,
        realized_gain_repository: RealizedGainRepository
    ):
        self.trade_repository = trade_repository
        self.holding_service = holding_service
        self.realized_gain_repository = realized_gain_repository

    def validate_trade_type(self, trade_type: str) -> None:
        if trade_type.lower() not in ["buy", "sell"]:
            raise ValueError(f"Invalid trade type: {trade_type}. Must be buy or sell.")

    def process_trade(self, trade_type: str, **kwargs) -> Trade:
        self.validate_trade_type(trade_type)
        if trade_type.lower() == "buy":
            return self.process_buy_trade(**kwargs)
        elif trade_type.lower() == "sell":
            return self.process_sell_trade(**kwargs)
        
        raise ValueError(f"Unhandled trade type: {trade_type}")

    def process_buy_trade(
        self,
        user_id: UUID,
        instrument_id: UUID,
        broker_connection_id: UUID,
        broker_trade_id: str,
        quantity: Decimal,
        price: Decimal,
        execution_time: datetime,
        idempotency_hash: str
    ) -> Trade:
        execution_time = _to_utc(execution_time)

        trade = self.trade_repository.create_trade(
            user_id=user_id,
            instrument_id=instrument_id,
            broker_connection_id=broker_connection_id,
            broker_trade_id=broker_trade_id,
            trade_type="buy",
            quantity=quantity,
            price=price,
            execution_time=execution_time,
            idempotency_hash=idempotency_hash
        )

        self.holding_service.create_holding_lot(
            user_id=user_id,
            broker_connection_id=broker_connection_id,
            instrument_id=instrument_id,
            source_trade_id=trade.id,
            quantity=quantity,
            buy_price=price,
            buy_date=execution_time
        )

        return trade

    def process_sell_trade(
        self,
        user_id: UUID,
        instrument_id: UUID,
        broker_connection_id: UUID,
        broker_trade_id: str,
        quantity: Decimal,
        price: Decimal,
        execution_time: datetime,
        idempotency_hash: str
    ) -> Trade:
        execution_time = _to_utc(execution_time)

        trade = self.trade_repository.create_trade(
            user_id=user_id,
            instrument_id=instrument_id,
            broker_connection_id=broker_connection_id,
            broker_trade_id=broker_trade_id,
            trade_type="sell",
            quantity=quantity,
            price=price,
            execution_time=execution_time,
            idempotency_hash=idempotency_hash
        )

        consumption_breakdown = self.holding_service.consume_lots_fifo(
            user_id=user_id,
            instrument_id=instrument_id,
            sell_quantity=quantity,
            sell_price=price,
            sell_date=execution_time
        )

        for breakdown_entry in consumption_breakdown:
            self.realized_gain_repository.create_realized_gain(
                user_id=user_id,
                sell_trade_id=trade.id,
                holding_lot_id=breakdown_entry["lot_id"],
                instrument_id=instrument_id,
                quantity_sold=breakdown_entry["quantity_consumed"],
                buy_price=breakdown_entry["buy_price"],
                sell_price=breakdown_entry["sell_price"],
                buy_date=breakdown_entry["buy_date"],
                sell_date=breakdown_entry["sell_date"],
                holding_days=breakdown_entry["holding_days"],
                gain_type=breakdown_entry["gain_type"],
                profit_loss=breakdown_entry["profit_loss"],
            )

        return trade

    def process_fno_sell_trade(
        self,
        user_id: UUID,
        instrument_id: UUID,
        broker_connection_id: UUID,
        broker_trade_id: str,
        quantity: Decimal,
        price: Decimal,
        execution_time: datetime,
        idempotency_hash: str,
    ) -> Trade:
        # F&O sell trades are stored but NOT processed
        # through FIFO or realized_gains.
        # F&O P&L calculation is deferred to Phase 5.3
        # which will build a dedicated F&O engine.
        trade = self.trade_repository.create_trade(
            user_id=user_id,
            instrument_id=instrument_id,
            broker_connection_id=broker_connection_id,
            broker_trade_id=broker_trade_id,
            trade_type="sell",
            quantity=quantity,
            price=price,
            execution_time=execution_time,
            idempotency_hash=idempotency_hash,
        )
        return trade

    def process_fno_buy_trade(
        self,
        user_id: UUID,
        instrument_id: UUID,
        broker_connection_id: UUID,
        broker_trade_id: str,
        quantity: Decimal,
        price: Decimal,
        execution_time: datetime,
        idempotency_hash: str,
    ) -> Trade:
        # F&O buy trades are stored but NOT processed into
        # holding lots. Equity holding lots assume FIFO and
        # STCG/LTCG rules that do not apply to F&O.
        # F&O position reconstruction is deferred to Phase 5.3
        # which will build a dedicated F&O engine from stored trades.
        trade = self.trade_repository.create_trade(
            user_id=user_id,
            instrument_id=instrument_id,
            broker_connection_id=broker_connection_id,
            broker_trade_id=broker_trade_id,
            trade_type="buy",
            quantity=quantity,
            price=price,
            execution_time=execution_time,
            idempotency_hash=idempotency_hash,
        )
        return trade

    def get_trades_by_user(
        self,
        user_id: UUID
    ) -> list[Trade]:
        return self.trade_repository.get_by_user(user_id)

    def get_trade_by_id(
        self,
        trade_id: UUID
    ) -> Trade | None:
        return self.trade_repository.get_by_id(trade_id)
