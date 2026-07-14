from decimal import Decimal
from uuid import UUID

from app.core.tax_utils import get_assessment_year
from app.repositories.fno_pnl_repository import FnoPnlRepository
from app.repositories.trade_repository import TradeRepository

ZERO = Decimal("0")


class FnoPnlService:
    """
    F&O P&L engine. Matches F&O buys against sells using FIFO (by execution
    time) and produces business-income P&L entries — completely separate from
    the equity FIFO / realized_gains engine.

    calculate_all_fno_pnl() is delete-and-rebuild: it wipes the user's
    fno_pnl_entries and recomputes them from trades. This makes it a
    deterministic reconstruction engine — entries are always rebuildable
    from the source-of-truth trades.
    """

    def __init__(
        self,
        fno_pnl_repository: FnoPnlRepository,
        trade_repository: TradeRepository,
    ):
        self.fno_pnl_repository = fno_pnl_repository
        self.trade_repository = trade_repository

    def _group_fno_trades(self, user_id: UUID) -> dict:
        """
        Returns {instrument_id: {"symbol": str, "buys": [Trade], "sells": [Trade]}}
        for F&O instruments only. Equity/crypto trades are ignored.

        Scoped to instrument_type="fno" at the SQL level (a JOIN + WHERE in
        TradeRepository), not fetched-all-then-filtered-in-Python — fewer
        rows transferred, and instrument is eager-loaded so touching
        trade.instrument below triggers zero extra round trips.
        """
        fno_trades = self.trade_repository.get_by_user_and_instrument_type(
            user_id=user_id, instrument_type="fno"
        )
        grouped: dict = {}
        for trade in fno_trades:
            instrument = trade.instrument
            group = grouped.setdefault(
                trade.instrument_id,
                {"symbol": instrument.symbol, "buys": [], "sells": []},
            )
            if trade.trade_type == "buy":
                group["buys"].append(trade)
            else:
                group["sells"].append(trade)
        return grouped

    def calculate_all_fno_pnl(self, user_id: UUID) -> dict:
        # Delete-and-rebuild: wipe existing entries, recompute from trades.
        self.fno_pnl_repository.delete_by_user(user_id=user_id)

        grouped = self._group_fno_trades(user_id=user_id)

        instruments_processed = 0
        realized_entries_created = 0
        total_pnl = ZERO

        for instrument_id, data in grouped.items():
            instruments_processed += 1
            symbol = data["symbol"]
            buys = sorted(data["buys"], key=lambda t: t.execution_time)
            sells = sorted(data["sells"], key=lambda t: t.execution_time)

            # FIFO buy queue: each item = [remaining_qty, buy_trade]
            buy_queue = [[Decimal(str(b.quantity)), b] for b in buys]
            bi = 0  # pointer to current buy lot

            for sell in sells:
                sell_remaining = Decimal(str(sell.quantity))
                sell_price = Decimal(str(sell.price))
                sell_time = sell.execution_time
                ay = get_assessment_year(sell_time)

                while sell_remaining > ZERO:
                    # advance past exhausted buy lots
                    while bi < len(buy_queue) and buy_queue[bi][0] <= ZERO:
                        bi += 1

                    if bi >= len(buy_queue):
                        # No buy left to match — expired / shorted sell.
                        # Option A: buy_price = 0, profit_loss = sell_price * qty
                        match_qty = sell_remaining
                        profit_loss = sell_price * match_qty
                        self.fno_pnl_repository.create_entry(
                            user_id=user_id,
                            instrument_id=instrument_id,
                            buy_trade_id=None,
                            sell_trade_id=sell.id,
                            symbol=symbol,
                            quantity=match_qty,
                            buy_price=ZERO,
                            sell_price=sell_price,
                            buy_time=None,
                            sell_time=sell_time,
                            profit_loss=profit_loss,
                            is_intraday=False,
                            assessment_year=ay,
                        )
                        realized_entries_created += 1
                        total_pnl += profit_loss
                        sell_remaining = ZERO
                        break

                    buy_item = buy_queue[bi]
                    buy_remaining = buy_item[0]
                    buy_trade = buy_item[1]
                    buy_price = Decimal(str(buy_trade.price))
                    buy_time = buy_trade.execution_time

                    match_qty = min(sell_remaining, buy_remaining)
                    profit_loss = (sell_price - buy_price) * match_qty
                    is_intraday = buy_time.date() == sell_time.date()

                    self.fno_pnl_repository.create_entry(
                        user_id=user_id,
                        instrument_id=instrument_id,
                        buy_trade_id=buy_trade.id,
                        sell_trade_id=sell.id,
                        symbol=symbol,
                        quantity=match_qty,
                        buy_price=buy_price,
                        sell_price=sell_price,
                        buy_time=buy_time,
                        sell_time=sell_time,
                        profit_loss=profit_loss,
                        is_intraday=is_intraday,
                        assessment_year=ay,
                    )
                    realized_entries_created += 1
                    total_pnl += profit_loss

                    buy_item[0] = buy_remaining - match_qty
                    sell_remaining = sell_remaining - match_qty

        # Open positions counted per instrument (net unmatched buy quantity),
        # consistent with _compute_open_positions / GET /fno/pnl and /fno/positions.
        open_positions_count = len(self._compute_open_positions(user_id=user_id))

        return {
            "instruments_processed": instruments_processed,
            "realized_entries_created": realized_entries_created,
            "open_positions_count": open_positions_count,
            "total_pnl": total_pnl,
        }

    def _compute_open_positions(self, user_id: UUID) -> list[dict]:
        """
        Derive open F&O positions (unmatched buys) from trades. Consumes total
        sold quantity against buys in FIFO order; whatever buy quantity remains
        is open. Weighted-average buy price over the remaining lots.
        """
        grouped = self._group_fno_trades(user_id=user_id)
        positions: list[dict] = []

        for instrument_id, data in grouped.items():
            buys = sorted(data["buys"], key=lambda t: t.execution_time)
            sells = data["sells"]

            total_sold = sum(
                (Decimal(str(s.quantity)) for s in sells),
                ZERO,
            )

            buy_queue = [
                [Decimal(str(b.quantity)), Decimal(str(b.price))] for b in buys
            ]

            remaining_to_consume = total_sold
            for item in buy_queue:
                if remaining_to_consume <= ZERO:
                    break
                take = min(item[0], remaining_to_consume)
                item[0] -= take
                remaining_to_consume -= take

            open_qty = sum((item[0] for item in buy_queue), ZERO)
            if open_qty > ZERO:
                total_cost = sum(
                    (item[0] * item[1] for item in buy_queue),
                    ZERO,
                )
                avg_buy_price = total_cost / open_qty
                positions.append(
                    {
                        "instrument_id": instrument_id,
                        "symbol": data["symbol"],
                        "open_quantity": open_qty,
                        "avg_buy_price": avg_buy_price,
                    }
                )

        return positions

    def get_pnl_summary(
        self,
        user_id: UUID,
        assessment_year: str | None = None,
    ) -> dict:
        if assessment_year:
            entries = self.fno_pnl_repository.get_by_user_and_ay(
                user_id=user_id,
                assessment_year=assessment_year,
            )
        else:
            entries = self.fno_pnl_repository.get_by_user(user_id=user_id)

        total_pnl = ZERO
        intraday_pnl = ZERO
        positional_pnl = ZERO
        for entry in entries:
            pl = Decimal(str(entry.profit_loss))
            total_pnl += pl
            if entry.is_intraday:
                intraday_pnl += pl
            else:
                positional_pnl += pl

        open_positions = self._compute_open_positions(user_id=user_id)

        return {
            "total_pnl": total_pnl,
            "intraday_pnl": intraday_pnl,
            "positional_pnl": positional_pnl,
            "realized_entry_count": len(entries),
            "open_positions": open_positions,
            "entries": entries,
        }

    def get_open_positions(self, user_id: UUID) -> list[dict]:
        return self._compute_open_positions(user_id=user_id)
