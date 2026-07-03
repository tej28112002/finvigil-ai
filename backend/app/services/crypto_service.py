from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.models.trade import Trade
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.tds_ledger_repository import TdsLedgerRepository
from app.repositories.trade_repository import TradeRepository
from app.services.holding_service import HoldingLotService

# 1% TDS on the sale consideration of a VDA transfer, when the sell value
# exceeds the per-transaction threshold. ₹10,000 is the common-case threshold
# (₹50,000 for specified persons — MVP uses the ₹10,000 case).
CRYPTO_TDS_RATE = Decimal("0.01")
CRYPTO_TDS_THRESHOLD = Decimal("10000")

INCOME_TYPE_CRYPTO = "crypto_vda"


class CryptoService:
    """
    Crypto / VDA trade processing. Reuses the equity FIFO machinery
    (HoldingLotService.create_holding_lot + consume_lots_fifo) for cost basis,
    but writes realized_gains with income_type='crypto_vda' and gain_type=None
    (VDA has no STCG/LTCG), and records 1% TDS on qualifying sells.

    Kept separate from TradeService so the equity/F&O engines are untouched.
    """

    def __init__(
        self,
        instrument_repository: InstrumentRepository,
        trade_repository: TradeRepository,
        holding_service: HoldingLotService,
        realized_gain_repository: RealizedGainRepository,
        tds_ledger_repository: TdsLedgerRepository,
    ):
        self.instrument_repository = instrument_repository
        self.trade_repository = trade_repository
        self.holding_service = holding_service
        self.realized_gain_repository = realized_gain_repository
        self.tds_ledger_repository = tds_ledger_repository

    def ingest_crypto_trade(
        self,
        user_id: UUID,
        broker_connection_id: UUID,
        broker_trade_id: str,
        trade_type: str,
        symbol: str,
        instrument_name: str,
        quantity: Decimal,
        price: Decimal,
        execution_time: datetime,
        idempotency_hash: str,
        isin: str | None = None,
    ) -> Trade:
        if trade_type.lower() not in ("buy", "sell"):
            raise ValueError(
                f"Invalid trade type: {trade_type}. Must be buy or sell."
            )

        # Normalize naive timestamps to UTC — the DB stores TIMESTAMPTZ, so
        # buy_date read back during FIFO is tz-aware and a naive sell_date
        # would fail to subtract.
        if execution_time.tzinfo is None:
            execution_time = execution_time.replace(tzinfo=timezone.utc)

        instrument = self.instrument_repository.get_or_create(
            symbol=symbol,
            instrument_type="crypto",
            name=instrument_name,
            isin=isin,
        )

        if trade_type.lower() == "buy":
            return self._process_crypto_buy(
                user_id=user_id,
                instrument_id=instrument.id,
                broker_connection_id=broker_connection_id,
                broker_trade_id=broker_trade_id,
                quantity=quantity,
                price=price,
                execution_time=execution_time,
                idempotency_hash=idempotency_hash,
            )
        return self._process_crypto_sell(
            user_id=user_id,
            instrument_id=instrument.id,
            broker_connection_id=broker_connection_id,
            broker_trade_id=broker_trade_id,
            quantity=quantity,
            price=price,
            execution_time=execution_time,
            idempotency_hash=idempotency_hash,
        )

    def _process_crypto_buy(
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
        self.holding_service.create_holding_lot(
            user_id=user_id,
            broker_connection_id=broker_connection_id,
            instrument_id=instrument_id,
            source_trade_id=trade.id,
            quantity=quantity,
            buy_price=price,
            buy_date=execution_time,
        )
        return trade

    def _process_crypto_sell(
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

        # FIFO cost basis — same engine as equity, but the realized rows are
        # tagged crypto_vda with gain_type=None.
        consumption_breakdown = self.holding_service.consume_lots_fifo(
            user_id=user_id,
            instrument_id=instrument_id,
            sell_quantity=quantity,
            sell_price=price,
            sell_date=execution_time,
        )
        for entry in consumption_breakdown:
            self.realized_gain_repository.create_realized_gain(
                user_id=user_id,
                sell_trade_id=trade.id,
                holding_lot_id=entry["lot_id"],
                instrument_id=instrument_id,
                quantity_sold=entry["quantity_consumed"],
                buy_price=entry["buy_price"],
                sell_price=entry["sell_price"],
                buy_date=entry["buy_date"],
                sell_date=entry["sell_date"],
                holding_days=entry["holding_days"],
                gain_type=None,
                profit_loss=entry["profit_loss"],
                income_type=INCOME_TYPE_CRYPTO,
            )

        # 1% TDS on the sale consideration if above the threshold.
        sell_value = price * quantity
        if sell_value > CRYPTO_TDS_THRESHOLD:
            tds_amount = sell_value * CRYPTO_TDS_RATE
            self.tds_ledger_repository.create_entry(
                user_id=user_id,
                source_trade_id=trade.id,
                amount=tds_amount,
                timestamp=execution_time,
            )

        return trade
