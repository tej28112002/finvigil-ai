"""
XIRR and Alpha computation from trade history.

XIRR is the annualized rate of return that makes the net present value of
all cash flows (buys as negative outflows, sells + current portfolio value as
positive inflows) equal to zero.  Algorithm: scipy.optimize.brentq.

Alpha = portfolio XIRR − Nifty 50 XIRR for the same cash-flow schedule.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.trade_repository import TradeRepository
from app.services.nifty_service import NiftyService


def _run_xirr_cashflows(cashflows: list[tuple[date, Decimal]]) -> float | None:
    """
    Pure-math XIRR over a list of (date, amount) tuples.
    Exposed at module level so unit tests can call it without any DB.

    Returns the annualised rate (e.g. 0.18 for 18 %) or None when brentq
    cannot find a sign change in [-0.999, 100].
    """
    from scipy.optimize import brentq

    sorted_cfs = sorted(cashflows, key=lambda x: x[0])
    min_date = sorted_cfs[0][0]

    def npv(rate: float) -> float:
        return sum(
            float(amount) / (1 + rate) ** ((d - min_date).days / 365.0)
            for d, amount in sorted_cfs
        )

    try:
        return brentq(npv, -0.999, 100.0)
    except ValueError:
        return None


class XirrService:
    def __init__(
        self,
        trade_repository: TradeRepository,
        holding_repository: HoldingLotRepository,
        dashboard_repository: DashboardRepository,
        nifty_service: NiftyService,
        realized_gain_repository: RealizedGainRepository | None = None,
    ):
        self.trade_repo = trade_repository
        self.holding_repo = holding_repository
        self.dashboard_repo = dashboard_repository
        self.nifty_service = nifty_service
        self.realized_gain_repo = realized_gain_repository

    def _build_trade_cashflows(self, user_id: UUID) -> list[tuple[date, Decimal]]:
        """BUY trades → negative amounts; SELL trades → positive amounts.
        Sorted ascending by date.  Does NOT include the terminal value."""
        trades = self.trade_repo.get_by_user(user_id)
        cashflows: list[tuple[date, Decimal]] = []
        for trade in trades:
            qty = Decimal(str(trade.quantity))
            price = Decimal(str(trade.price))
            amount = qty * price
            t_date = trade.execution_time.date()
            if trade.trade_type == "buy":
                cashflows.append((t_date, -amount))
            else:
                cashflows.append((t_date, amount))
        cashflows.sort(key=lambda x: x[0])
        return cashflows

    def _get_current_equity_value(self, user_id: UUID) -> Decimal:
        """Try the cached dashboard projection first; fall back to cost basis
        of open/partial lots if no projection exists or it is zero."""
        projection = self.dashboard_repo.get_by_user(user_id)
        if projection:
            val = Decimal(str(projection.total_equity_value))
            if val > Decimal("0"):
                return val

        active_lots = self.holding_repo.get_active_lots_by_user(user_id)
        total = sum(
            Decimal(str(lot.quantity_remaining)) * Decimal(str(lot.buy_price))
            for lot in active_lots
        )
        return total

    def _xirr_from_trade_cashflows(
        self, trade_cfs: list[tuple[date, Decimal]], user_id: UUID
    ) -> float | None:
        """Attach today's equity value as terminal inflow and run XIRR."""
        current_value = self._get_current_equity_value(user_id)
        if current_value == Decimal("0"):
            return None

        all_cfs = trade_cfs + [(date.today(), current_value)]
        if len(all_cfs) < 2:
            return None

        has_negative = any(a < Decimal("0") for _, a in all_cfs)
        has_positive = any(a > Decimal("0") for _, a in all_cfs)
        if not (has_negative and has_positive):
            return None

        return _run_xirr_cashflows(all_cfs)

    def compute_xirr_and_alpha(
        self, user_id: UUID
    ) -> tuple[float | None, float | None]:
        """Returns (xirr, alpha).  Single trade-repository call for both."""
        trade_cfs = self._build_trade_cashflows(user_id)
        xirr = self._xirr_from_trade_cashflows(trade_cfs, user_id)

        if xirr is None or not trade_cfs:
            return xirr, None

        nifty_xirr = self.nifty_service.get_nifty_xirr(trade_cfs)
        alpha = (xirr - nifty_xirr) if nifty_xirr is not None else None

        return xirr, alpha

    def get_current_value(self, user_id: UUID) -> float | None:
        """Public float wrapper around _get_current_equity_value, for callers
        outside this service (e.g. the API layer) that need the raw rupee
        value without reaching into a private method."""
        val = self._get_current_equity_value(user_id)
        return float(val) if val > Decimal("0") else None

    def _get_total_invested(self, user_id: UUID) -> Decimal:
        """Reconstructs total capital ever deployed at original cost basis:
        what's still held (quantity_remaining across every lot, open or
        closed) plus what was already sold (quantity_sold * buy_price from
        realized_gains). Closed lots contribute 0 via quantity_remaining, so
        their cost basis only shows up through the realized_gains side."""
        all_lots = self.holding_repo.get_by_user(user_id)
        lots_total = sum(
            (
                Decimal(str(lot.quantity_remaining)) * Decimal(str(lot.buy_price))
                for lot in all_lots
            ),
            Decimal("0"),
        )
        realized_gains = self.realized_gain_repo.get_by_user(user_id)
        realized_total = sum(
            (
                Decimal(str(rg.quantity_sold)) * Decimal(str(rg.buy_price))
                for rg in realized_gains
            ),
            Decimal("0"),
        )
        return lots_total + realized_total

    def compute_absolute_return(self, user_id: UUID) -> float | None:
        invested = self._get_total_invested(user_id)
        if invested == Decimal("0"):
            return None

        current_value = self._get_current_equity_value(user_id)
        realized_gains = self.realized_gain_repo.get_by_user(user_id)
        realized_total = sum(
            (Decimal(str(rg.profit_loss)) for rg in realized_gains), Decimal("0")
        )
        total_current = current_value + realized_total

        return float((total_current - invested) / invested * 100)

    def compute_cagr(self, user_id: UUID) -> float | None:
        all_lots = self.holding_repo.get_by_user(user_id)
        if not all_lots:
            return None

        earliest_buy_date = min(lot.buy_date for lot in all_lots).date()
        years = (date.today() - earliest_buy_date).days / 365.0
        if years < 0.1:
            return None

        invested = self._get_total_invested(user_id)
        if invested == Decimal("0"):
            return None

        current_value = self._get_current_equity_value(user_id)
        ratio = float(current_value) / float(invested)
        if ratio < 0:
            return None

        cagr = ratio ** (1.0 / years) - 1
        return float(cagr * 100)

    def compute_asset_allocation(self, user_id: UUID) -> dict[str, float] | None:
        lots = self.holding_repo.get_active_lots_by_user(user_id)
        if not lots:
            return None

        totals: dict[str, Decimal] = {}
        total_invested = Decimal("0")
        for lot in lots:
            itype = lot.instrument.instrument_type
            amount = Decimal(str(lot.quantity_remaining)) * Decimal(str(lot.buy_price))
            totals[itype] = totals.get(itype, Decimal("0")) + amount
            total_invested += amount

        if total_invested == Decimal("0"):
            return None

        return {k: float(v / total_invested * 100) for k, v in totals.items()}

    def compute_concentration(self, user_id: UUID) -> list[dict] | None:
        lots = self.holding_repo.get_active_lots_by_user(user_id)
        if not lots:
            return None

        by_symbol: dict[str, dict] = {}
        total_invested = Decimal("0")
        for lot in lots:
            symbol = lot.instrument.symbol
            amount = Decimal(str(lot.quantity_remaining)) * Decimal(str(lot.buy_price))
            if symbol not in by_symbol:
                by_symbol[symbol] = {
                    "invested": Decimal("0"),
                    "instrument_type": lot.instrument.instrument_type,
                }
            by_symbol[symbol]["invested"] += amount
            total_invested += amount

        if total_invested == Decimal("0"):
            return None

        rows = [
            {
                "symbol": symbol,
                "weight": float(data["invested"] / total_invested * 100),
                "instrument_type": data["instrument_type"],
            }
            for symbol, data in by_symbol.items()
        ]
        rows.sort(key=lambda r: r["weight"], reverse=True)
        return rows[:5]
