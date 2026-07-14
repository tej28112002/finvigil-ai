from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.models.replay_run import ReplayRun
from app.models.replay_scenario import ReplayScenario
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.replay_repository import ReplayRunRepository, ReplayScenarioRepository
from app.repositories.trade_repository import TradeRepository

ZERO = Decimal("0")


def _to_utc(dt: datetime) -> datetime:
    """Same normalization as trade_service._to_utc / crypto_service — the
    DB stores TIMESTAMPTZ, so a naive datetime read from JSONB parameters
    would fail to compare against a tz-aware trade.execution_time."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class ReplayService:
    """
    Portfolio Replay: rewinds a user's EQUITY portfolio to any past date by
    replaying their real trades (source of truth) through the same FIFO
    logic as HoldingLotService.consume_lots_fifo, plus optional
    hypothetical "what-if" trades layered on top for scenario planning
    (BRD FR-REP-01).

    Deliberately does NOT touch holding_lots / realized_gains — those are
    the live, present-day derived tables (rebuildable by the Phase 5.3
    reconstruction engine). A replay is a separate, parallel, purely
    in-memory computation persisted only as a JSONB snapshot on ReplayRun,
    so re-running the same scenario later (as real trades accumulate) never
    corrupts anything real.

    Scope (v1): equity only, matching reconstruction_service's equity-only
    boundary — F&O is business income with no holding-period concept and
    crypto has flat 30% tax with no set-off, so both would need their own
    replay variants; deferred, same as they were originally deferred from
    the equity reconstruction engine.

    No historical/live pricing is applied — this schema has no EOD price
    history table yet (BRD FR-REP-02's price stack is a separate,
    undelivered phase), so holdings are valued at FIFO cost basis only,
    never mark-to-market. Disclosed via ReplayResultData.disclaimer, not
    silently approximated.
    """

    def __init__(
        self,
        trade_repository: TradeRepository,
        instrument_repository: InstrumentRepository,
        replay_scenario_repository: ReplayScenarioRepository,
        replay_run_repository: ReplayRunRepository,
    ):
        self.trade_repository = trade_repository
        self.instrument_repository = instrument_repository
        self.replay_scenario_repository = replay_scenario_repository
        self.replay_run_repository = replay_run_repository

    # ---- Scenario CRUD ----

    def create_scenario(
        self,
        user_id: UUID,
        name: str,
        parameters: dict,
    ) -> ReplayScenario:
        return self.replay_scenario_repository.create_scenario(
            user_id=user_id,
            name=name,
            parameters=parameters,
        )

    def list_scenarios(self, user_id: UUID) -> list[ReplayScenario]:
        return self.replay_scenario_repository.get_by_user(user_id=user_id)

    def get_scenario(
        self, user_id: UUID, scenario_id: UUID
    ) -> ReplayScenario | None:
        return self.replay_scenario_repository.get_by_id_and_user(
            scenario_id=scenario_id,
            user_id=user_id,
        )

    def delete_scenario(self, user_id: UUID, scenario_id: UUID) -> bool:
        scenario = self.get_scenario(user_id=user_id, scenario_id=scenario_id)
        if not scenario:
            return False
        self.replay_scenario_repository.delete(scenario)
        return True

    # ---- Runs ----

    def list_runs(self, user_id: UUID, scenario_id: UUID) -> list[ReplayRun]:
        return self.replay_run_repository.get_by_scenario(
            scenario_id=scenario_id,
            user_id=user_id,
        )

    def get_run(self, user_id: UUID, run_id: UUID) -> ReplayRun | None:
        return self.replay_run_repository.get_by_id_and_user(
            run_id=run_id,
            user_id=user_id,
        )

    def run_scenario(self, user_id: UUID, scenario_id: UUID) -> ReplayRun | None:
        """
        Returns None if the scenario doesn't exist / isn't owned by this
        user (caller maps that to 404). Raises ValueError for a malformed
        what-if trade (unknown symbol, or a sell the replay can't satisfy) —
        caller maps that to 400. Keeping these as two different signaling
        mechanisms lets the API layer tell "not yours" apart from "your
        scenario data is bad" without a second lookup.
        """
        scenario = self.get_scenario(user_id=user_id, scenario_id=scenario_id)
        if not scenario:
            return None

        params = scenario.parameters
        as_of_date = _to_utc(datetime.fromisoformat(params["as_of_date"]))

        equity_trades = [
            t
            for t in self.trade_repository.get_by_user_and_instrument_type(
                user_id=user_id, instrument_type="equity"
            )
            if _to_utc(t.execution_time) <= as_of_date
        ]

        events = [
            {
                "instrument_id": t.instrument_id,
                "symbol": t.instrument.symbol,
                "trade_type": t.trade_type,
                "quantity": Decimal(str(t.quantity)),
                "price": Decimal(str(t.price)),
                "execution_time": _to_utc(t.execution_time),
            }
            for t in equity_trades
        ]

        what_if_applied = 0
        for wt in params.get("what_if_trades", []):
            wt_time = _to_utc(datetime.fromisoformat(wt["execution_time"]))
            if wt_time > as_of_date:
                # A what-if trade dated after the rewind point can't affect
                # this snapshot — skipped, not an error.
                continue
            instrument = self.instrument_repository.get_by_symbol(wt["symbol"])
            if not instrument:
                raise ValueError(f"Unknown instrument symbol: {wt['symbol']}")
            events.append(
                {
                    "instrument_id": instrument.id,
                    "symbol": instrument.symbol,
                    "trade_type": wt["trade_type"],
                    "quantity": Decimal(str(wt["quantity"])),
                    "price": Decimal(str(wt["price"])),
                    "execution_time": wt_time,
                }
            )
            what_if_applied += 1

        events.sort(key=lambda e: e["execution_time"])

        result = self._replay_fifo(events)
        result["as_of_date"] = as_of_date.isoformat()
        result["trades_replayed"] = len(equity_trades)
        result["what_if_trades_applied"] = what_if_applied
        result["disclaimer"] = (
            "Portfolio Replay reconstructs invested capital and realized "
            "P&L from your trade history as of the selected date using "
            "FIFO cost basis. It does not apply historical or live market "
            "prices, so it is not a mark-to-market valuation as of that "
            "date. What-if trades are hypothetical and are never written "
            "to your real holdings. Not financial advice — consult your CA."
        )

        return self.replay_run_repository.create_run(
            user_id=user_id,
            replay_scenario_id=scenario.id,
            result_data=result,
        )

    def _replay_fifo(self, events: list[dict]) -> dict:
        """
        Pure in-memory FIFO replay over a chronologically sorted event list.
        Mirrors HoldingLotService.consume_lots_fifo's matching logic (a
        buy-queue per instrument, oldest lot consumed first) but keeps every
        lot in a local list instead of the holding_lots table — nothing
        here is written to the database.
        """
        open_lots: dict[UUID, list[dict]] = defaultdict(list)
        realized_pnl = ZERO

        for event in events:
            instrument_id = event["instrument_id"]
            quantity = event["quantity"]
            price = event["price"]

            if event["trade_type"] == "buy":
                open_lots[instrument_id].append(
                    {
                        "quantity_remaining": quantity,
                        "buy_price": price,
                    }
                )
                continue

            # sell — consume FIFO from this instrument's lot queue
            remaining = quantity
            lots = open_lots[instrument_id]
            for lot in lots:
                if remaining <= ZERO:
                    break
                if lot["quantity_remaining"] <= ZERO:
                    continue
                consumed = min(remaining, lot["quantity_remaining"])
                realized_pnl += (price - lot["buy_price"]) * consumed
                lot["quantity_remaining"] -= consumed
                remaining -= consumed

            if remaining > ZERO:
                raise ValueError(
                    f"Replay cannot sell {quantity} of {event['symbol']} on "
                    f"{event['execution_time'].date()} — only "
                    f"{quantity - remaining} were held at that point in the "
                    "replay. Check what-if trade quantities/ordering."
                )

            open_lots[instrument_id] = [
                lot for lot in lots if lot["quantity_remaining"] > ZERO
            ]

        holdings = []
        total_invested = ZERO
        for instrument_id, lots in open_lots.items():
            if not lots:
                continue
            total_qty = sum((lot["quantity_remaining"] for lot in lots), ZERO)
            if total_qty <= ZERO:
                continue
            invested_value = sum(
                (lot["quantity_remaining"] * lot["buy_price"] for lot in lots),
                ZERO,
            )
            avg_buy_price = invested_value / total_qty
            symbol = next(
                e["symbol"] for e in events if e["instrument_id"] == instrument_id
            )
            holdings.append(
                {
                    "instrument_id": str(instrument_id),
                    "symbol": symbol,
                    "quantity": str(total_qty),
                    "avg_buy_price": str(avg_buy_price),
                    "invested_value": str(invested_value),
                }
            )
            total_invested += invested_value

        holdings.sort(key=lambda h: h["symbol"])

        return {
            "holdings": holdings,
            "total_invested": str(total_invested),
            "realized_pnl_to_date": str(realized_pnl),
        }
