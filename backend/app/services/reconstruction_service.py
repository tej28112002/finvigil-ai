from decimal import Decimal
from uuid import UUID

from app.repositories.corporate_action_repository import CorporateActionRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.trade_repository import TradeRepository
from app.services.holding_service import HoldingLotService

ZERO = Decimal("0")


class ReconstructionService:
    """
    Equity reconstruction engine — rebuilds holding_lots and realized_gains
    from the source-of-truth trades + corporate_action_adjustments.

    Delete-and-rebuild, fully idempotent: running it repeatedly always yields
    the same derived state. This closes the KNOWN PRODUCTION RISK (Section 5):
    holding_lots / realized_gains were previously unrebuildable if corrupted.

    Reuses HoldingLotService (create_holding_lot + consume_lots_fifo) so the
    replay is byte-identical to the live buy/sell pipeline in trade_service.

    Replay order (matches the live pipeline and corporate_action_service):
      1. Replay ALL equity trades in execution_time order — buys create lots,
         sells consume lots FIFO and produce realized_gains.
      2. THEN reapply corporate actions as a post-pass (in applied_at order),
         adjusting open/partial lots bought strictly before applied_at.

    Corporate actions are applied AFTER trades (not chronologically
    interleaved) on purpose: it reproduces existing behavior exactly (a split
    only touches lots still open when it is applied), and matches the
    "reapply splits/bonuses after rebuilding lots" contract. F&O trades are
    ignored here — F&O has its own engine (fno_pnl_service).
    """

    def __init__(
        self,
        trade_repository: TradeRepository,
        holding_lot_repository: HoldingLotRepository,
        holding_service: HoldingLotService,
        realized_gain_repository: RealizedGainRepository,
        corporate_action_repository: CorporateActionRepository,
    ):
        self.trade_repository = trade_repository
        self.holding_lot_repository = holding_lot_repository
        self.holding_service = holding_service
        self.realized_gain_repository = realized_gain_repository
        self.corporate_action_repository = corporate_action_repository

    def rebuild_equity_for_user(self, user_id: UUID) -> dict:
        # STEP 1 — delete derived EQUITY data only. Scoped by income_type /
        # instrument_type so crypto_vda gains and crypto holding lots are left
        # intact (crypto has its own engine). realized_gains FIRST: its
        # holding_lot_id FK is ON DELETE RESTRICT, so holding_lots cannot be
        # deleted while gains reference them.
        realized_gains_deleted = (
            self.realized_gain_repository.delete_by_user_and_income_type(
                user_id=user_id,
                income_type="equity_capital_gains",
            )
        )
        holding_lots_deleted = (
            self.holding_lot_repository.delete_by_user_and_instrument_type(
                user_id=user_id,
                instrument_type="equity",
            )
        )

        # STEP 2 — fetch equity trades only, in chronological order. Scoped
        # to instrument_type="equity" at the SQL level (was: fetch every
        # trade the user has, then filter in Python via t.instrument, which
        # lazy-loaded one extra round trip per distinct instrument — see the
        # same fix in trade_repository.get_by_user()).
        equity_trades = self.trade_repository.get_by_user_and_instrument_type(
            user_id=user_id, instrument_type="equity"
        )
        equity_trades.sort(key=lambda t: t.execution_time)

        holding_lots_created = 0
        realized_gains_created = 0

        # STEP 3 — replay trades: buys create lots, sells consume FIFO.
        for trade in equity_trades:
            quantity = Decimal(str(trade.quantity))
            price = Decimal(str(trade.price))

            if trade.trade_type == "buy":
                self.holding_service.create_holding_lot(
                    user_id=user_id,
                    broker_connection_id=trade.broker_connection_id,
                    instrument_id=trade.instrument_id,
                    source_trade_id=trade.id,
                    quantity=quantity,
                    buy_price=price,
                    buy_date=trade.execution_time,
                )
                holding_lots_created += 1
            else:  # sell
                breakdown = self.holding_service.consume_lots_fifo(
                    user_id=user_id,
                    instrument_id=trade.instrument_id,
                    sell_quantity=quantity,
                    sell_price=price,
                    sell_date=trade.execution_time,
                )
                for entry in breakdown:
                    self.realized_gain_repository.create_realized_gain(
                        user_id=user_id,
                        sell_trade_id=trade.id,
                        holding_lot_id=entry["lot_id"],
                        instrument_id=trade.instrument_id,
                        quantity_sold=entry["quantity_consumed"],
                        buy_price=entry["buy_price"],
                        sell_price=entry["sell_price"],
                        buy_date=entry["buy_date"],
                        sell_date=entry["sell_date"],
                        holding_days=entry["holding_days"],
                        gain_type=entry["gain_type"],
                        profit_loss=entry["profit_loss"],
                    )
                    realized_gains_created += 1

        # STEP 4 — reapply corporate actions as a post-pass, in applied_at
        # order. Same math as corporate_action_service (qty × ratio,
        # price ÷ ratio) but WITHOUT creating new adjustment rows — the
        # corporate_action_adjustments table is source of truth and is not
        # touched.
        adjustments = self.corporate_action_repository.get_by_user(
            user_id=user_id
        )
        adjustments.sort(key=lambda a: a.applied_at)

        corporate_actions_reapplied = 0
        lots_adjusted_by_corporate_actions = 0

        for adjustment in adjustments:
            ratio = Decimal(str(adjustment.ratio))
            affected_lots = self.holding_lot_repository.get_open_lots_before_date(
                user_id=user_id,
                instrument_id=adjustment.instrument_id,
                before_date=adjustment.applied_at,
            )
            for lot in affected_lots:
                old_quantity_bought = Decimal(str(lot.quantity_bought))
                old_quantity_remaining = Decimal(str(lot.quantity_remaining))
                old_buy_price = Decimal(str(lot.buy_price))

                self.holding_lot_repository.apply_corporate_action_to_lot(
                    lot=lot,
                    new_quantity_bought=old_quantity_bought * ratio,
                    new_quantity_remaining=old_quantity_remaining * ratio,
                    new_buy_price=old_buy_price / ratio,
                )
                lots_adjusted_by_corporate_actions += 1

            corporate_actions_reapplied += 1

        return {
            "realized_gains_deleted": realized_gains_deleted,
            "holding_lots_deleted": holding_lots_deleted,
            "holding_lots_created": holding_lots_created,
            "realized_gains_created": realized_gains_created,
            "corporate_actions_reapplied": corporate_actions_reapplied,
            "lots_adjusted_by_corporate_actions": lots_adjusted_by_corporate_actions,
        }
