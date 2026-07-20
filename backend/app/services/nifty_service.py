"""
Nifty 50 benchmark XIRR.

Answers: "What XIRR would you have got by putting the same cash amounts at
the same dates into the Nifty 50 index instead of your actual stocks?"

The result is cached in memory for 24 hours to avoid repeated yfinance
round-trips.  No Redis — an in-process dict is sufficient.
"""

from __future__ import annotations

import time
from datetime import date, timedelta
from decimal import Decimal

# Module-level cache: key -> (unix_timestamp, xirr_or_None)
_NIFTY_CACHE: dict[str, tuple[float, float | None]] = {}

_CACHE_TTL = 86_400  # 24 h in seconds


def _nearest_prior_price(
    prices: dict[date, Decimal], target: date
) -> Decimal | None:
    """Return the Nifty closing price on `target`, or the most recent
    prior trading day if the market was closed that day."""
    candidates = [d for d in prices if d <= target]
    if not candidates:
        return None
    return prices[max(candidates)]


class NiftyService:
    def get_nifty_xirr(
        self, trade_cashflows: list[tuple[date, Decimal]]
    ) -> float | None:
        """
        Compute the hypothetical XIRR from replicating the user's buy/sell
        schedule against the Nifty 50 index.

        trade_cashflows: list of (date, amount) where BUY is negative and
        SELL is positive.  No terminal value — this method builds its own.

        Returns None on any error (network, empty price history, no sign change).
        """
        if not trade_cashflows:
            return None

        buy_cfs = [(d, a) for d, a in trade_cashflows if a < Decimal("0")]
        if not buy_cfs:
            return None

        earliest = min(d for d, _ in trade_cashflows)
        today = date.today()

        cache_key = f"nifty_xirr_{earliest}_{len(buy_cfs)}"
        if cache_key in _NIFTY_CACHE:
            ts, cached = _NIFTY_CACHE[cache_key]
            if time.time() - ts < _CACHE_TTL:
                return cached

        try:
            import yfinance as yf

            ticker = yf.Ticker("^NSEI")
            hist = ticker.history(
                start=str(earliest),
                end=str(today + timedelta(days=1)),
            )

            if hist.empty or "Close" not in hist.columns:
                return None

            prices: dict[date, Decimal] = {}
            for ts_idx, row in hist.iterrows():
                prices[ts_idx.date()] = Decimal(str(row["Close"]))

            if not prices:
                return None

            total_buy_amount = sum(abs(a) for _, a in buy_cfs)
            remaining_units = Decimal("0")
            nifty_cfs: list[tuple[date, Decimal]] = []

            for trade_date, amount in sorted(trade_cashflows, key=lambda x: x[0]):
                nifty_price = _nearest_prior_price(prices, trade_date)
                if nifty_price is None or nifty_price == Decimal("0"):
                    continue

                if amount < Decimal("0"):  # BUY
                    units = abs(amount) / nifty_price
                    remaining_units += units
                    nifty_cfs.append((trade_date, amount))
                else:  # SELL — sell proportional units at Nifty price on that date
                    if total_buy_amount > Decimal("0"):
                        proportion = amount / total_buy_amount
                        units_to_sell = min(
                            remaining_units * proportion, remaining_units
                        )
                        remaining_units -= units_to_sell
                        nifty_cfs.append((trade_date, units_to_sell * nifty_price))

            if remaining_units <= Decimal("0"):
                return None

            today_price = _nearest_prior_price(prices, today)
            if today_price is None:
                return None

            nifty_cfs.append((today, remaining_units * today_price))

            has_neg = any(a < Decimal("0") for _, a in nifty_cfs)
            has_pos = any(a > Decimal("0") for _, a in nifty_cfs)
            if not (has_neg and has_pos):
                return None

            from app.services.xirr_service import _run_xirr_cashflows

            result = _run_xirr_cashflows(nifty_cfs)
            _NIFTY_CACHE[cache_key] = (time.time(), result)
            return result

        except Exception:
            return None
