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

# Per-ticker daily close price series, 24h TTL (same pattern as _NIFTY_CACHE).
_PRICE_CACHE: dict[str, tuple[float, dict | None]] = {}

# Per-user aligned (portfolio_values, nifty_values) series, 1h TTL — shorter
# than the price cache because it also reflects the user's own trade history.
_PORTFOLIO_SERIES_CACHE: dict[str, tuple[float, tuple | None]] = {}
_PORTFOLIO_SERIES_TTL = 3_600  # 1 h in seconds


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
    # India 10-yr G-Sec yield, as a percentage. Update here if the risk-free
    # benchmark changes — every Sharpe/Sortino call reads it from one place.
    INDIA_RISK_FREE_RATE = 6.8

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

    def _get_cached_prices(
        self, ticker: str, start: date, end: date
    ) -> dict[date, Decimal] | None:
        """Daily Close prices for one yfinance ticker, cached 24h. Returns
        None (and caches the None) if the download fails or is empty — the
        same "skip this symbol" behavior get_nifty_xirr uses."""
        cache_key = f"prices_{ticker}_{start}_{end}"
        if cache_key in _PRICE_CACHE:
            ts, cached = _PRICE_CACHE[cache_key]
            if time.time() - ts < _CACHE_TTL:
                return cached

        import yfinance as yf

        hist = yf.Ticker(ticker).history(
            start=str(start), end=str(end + timedelta(days=1))
        )
        if hist.empty or "Close" not in hist.columns:
            _PRICE_CACHE[cache_key] = (time.time(), None)
            return None

        prices = {idx.date(): Decimal(str(row["Close"])) for idx, row in hist.iterrows()}
        _PRICE_CACHE[cache_key] = (time.time(), prices)
        return prices

    def _build_daily_series(
        self, user_id, lots: list, trades: list
    ) -> tuple[list[float], list[float]] | None:
        """
        Builds two aligned daily series — portfolio value and Nifty 50 value
        — over the user's trading history, for use by every Phase B metric.

        The holding_lots table has no per-lot sell_date (only RealizedGain
        does), so rather than approximate "was this lot open on day D" from
        status alone, this replays the actual trade history day by day: BUY
        adds quantity to that symbol, SELL removes it. That gives an exact
        point-in-time quantity per symbol per day, which the lot-status
        approach can't.

        Any symbol whose yfinance download fails is dropped from pricing
        (not the whole computation); any day where a currently-held symbol
        still has no price is skipped entirely, so both series stay aligned
        day-for-day. Returns None if fewer than 30 valid days result, or on
        any unexpected error (network, empty history, etc).
        """
        if not lots or not trades:
            return None

        cache_key = f"series_{user_id}_{len(trades)}"
        if cache_key in _PORTFOLIO_SERIES_CACHE:
            ts, cached = _PORTFOLIO_SERIES_CACHE[cache_key]
            if time.time() - ts < _PORTFOLIO_SERIES_TTL:
                return cached

        try:
            dated_trades = [t for t in trades if t.instrument is not None]
            if not dated_trades:
                return None

            earliest = min(t.execution_time.date() for t in dated_trades)
            today = date.today()
            if (today - earliest).days < 30:
                return None

            symbols = sorted({t.instrument.symbol for t in dated_trades})
            price_series: dict[str, dict[date, Decimal]] = {}
            for symbol in symbols:
                prices = self._get_cached_prices(f"{symbol.upper()}.NS", earliest, today)
                if prices:
                    price_series[symbol] = prices

            if not price_series:
                _PORTFOLIO_SERIES_CACHE[cache_key] = (time.time(), None)
                return None

            nifty_prices = self._get_cached_prices("^NSEI", earliest, today)
            if not nifty_prices:
                _PORTFOLIO_SERIES_CACHE[cache_key] = (time.time(), None)
                return None

            trading_days = sorted(
                set().union(*(p.keys() for p in price_series.values()))
                & set(nifty_prices.keys())
            )

            sorted_trades = sorted(dated_trades, key=lambda t: t.execution_time)

            portfolio_values: list[float] = []
            nifty_values: list[float] = []

            for day in trading_days:
                qty_by_symbol: dict[str, Decimal] = {}
                for t in sorted_trades:
                    if t.execution_time.date() > day:
                        break
                    symbol = t.instrument.symbol
                    qty = Decimal(str(t.quantity))
                    if t.trade_type == "buy":
                        qty_by_symbol[symbol] = qty_by_symbol.get(symbol, Decimal("0")) + qty
                    else:
                        qty_by_symbol[symbol] = qty_by_symbol.get(symbol, Decimal("0")) - qty

                day_value = Decimal("0")
                valid = True
                for symbol, qty in qty_by_symbol.items():
                    if qty <= Decimal("0"):
                        continue
                    prices = price_series.get(symbol)
                    price = _nearest_prior_price(prices, day) if prices else None
                    if price is None:
                        valid = False
                        break
                    day_value += qty * price

                nifty_price = _nearest_prior_price(nifty_prices, day)
                if not valid or nifty_price is None:
                    continue

                portfolio_values.append(float(day_value))
                nifty_values.append(float(nifty_price))

            if len(portfolio_values) < 30:
                _PORTFOLIO_SERIES_CACHE[cache_key] = (time.time(), None)
                return None

            result = (portfolio_values, nifty_values)
            _PORTFOLIO_SERIES_CACHE[cache_key] = (time.time(), result)
            return result

        except Exception:
            return None

    def _build_daily_portfolio_returns(
        self, user_id, lots: list, trades: list
    ) -> list[float] | None:
        series = self._build_daily_series(user_id, lots, trades)
        if series is None:
            return None
        portfolio_values, _ = series
        returns = [
            (portfolio_values[i] - portfolio_values[i - 1]) / portfolio_values[i - 1]
            for i in range(1, len(portfolio_values))
            if portfolio_values[i - 1] != 0
        ]
        return returns if len(returns) >= 30 else None

    def compute_beta(self, user_id, lots: list, trades: list) -> float | None:
        series = self._build_daily_series(user_id, lots, trades)
        if series is None:
            return None
        portfolio_values, nifty_values = series

        port_returns = [
            (portfolio_values[i] - portfolio_values[i - 1]) / portfolio_values[i - 1]
            for i in range(1, len(portfolio_values))
            if portfolio_values[i - 1] != 0
        ]
        nifty_returns = [
            (nifty_values[i] - nifty_values[i - 1]) / nifty_values[i - 1]
            for i in range(1, len(nifty_values))
            if nifty_values[i - 1] != 0
        ]
        n = min(len(port_returns), len(nifty_returns))
        if n < 30:
            return None
        port_returns, nifty_returns = port_returns[:n], nifty_returns[:n]

        import numpy as np

        cov_matrix = np.cov(port_returns, nifty_returns)
        covariance = cov_matrix[0][1]
        nifty_variance = np.var(nifty_returns)
        if nifty_variance == 0:
            return None

        return float(covariance / nifty_variance)

    def compute_volatility(self, user_id, lots: list, trades: list) -> float | None:
        daily_returns = self._build_daily_portfolio_returns(user_id, lots, trades)
        if daily_returns is None:
            return None

        import numpy as np

        daily_std = np.std(daily_returns)
        annualized = daily_std * np.sqrt(252)
        return float(annualized * 100)

    def compute_max_drawdown(self, user_id, lots: list, trades: list) -> float | None:
        series = self._build_daily_series(user_id, lots, trades)
        if series is None:
            return None
        portfolio_values, _ = series

        peak = portfolio_values[0]
        max_drawdown = 0.0
        for value in portfolio_values:
            if value > peak:
                peak = value
            if peak > 0:
                drawdown = (peak - value) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        return float(max_drawdown * 100)

    def compute_sharpe(
        self, user_id, lots: list, trades: list, xirr_percent: float | None
    ) -> float | None:
        """xirr_percent must be on the same percentage scale as volatility
        and INDIA_RISK_FREE_RATE (e.g. 18.0 for 18%), not the raw 0.18
        fraction XirrService.compute_xirr_and_alpha returns."""
        if xirr_percent is None:
            return None
        volatility = self.compute_volatility(user_id, lots, trades)
        if volatility is None or volatility == 0:
            return None
        return float((xirr_percent - self.INDIA_RISK_FREE_RATE) / volatility)

    def compute_sortino(
        self, user_id, lots: list, trades: list, xirr_percent: float | None
    ) -> float | None:
        """See compute_sharpe for the xirr_percent scale requirement."""
        if xirr_percent is None:
            return None
        daily_returns = self._build_daily_portfolio_returns(user_id, lots, trades)
        if daily_returns is None:
            return None

        downside_returns = [r for r in daily_returns if r < 0]
        if len(downside_returns) < 5:
            return None

        import numpy as np

        downside_deviation = float(np.std(downside_returns) * np.sqrt(252) * 100)
        if downside_deviation == 0:
            return None

        return float((xirr_percent - self.INDIA_RISK_FREE_RATE) / downside_deviation)

    def compute_var_95(
        self, user_id, lots: list, trades: list, current_value: float | None
    ) -> float | None:
        daily_returns = self._build_daily_portfolio_returns(user_id, lots, trades)
        if daily_returns is None:
            return None
        if current_value is None or current_value == 0:
            return None

        import numpy as np

        var_pct = np.percentile(daily_returns, 5)
        return float(abs(var_pct) * current_value)
