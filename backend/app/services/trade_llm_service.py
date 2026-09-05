import json
import logging
from collections import defaultdict
from datetime import date

import requests

logger = logging.getLogger("finvigil")

MAX_DETAILED_TRADES = 100
# Groq's OpenAI-compatible chat completions endpoint -- same api.groq.com
# host as app/core/groq_client.py's transcription call, called directly via
# requests (already a project dependency) rather than the `groq` SDK
# package, which isn't installed anywhere in this project.
_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class TradeLLMService:
    """
    Groq LLaMA-backed weekly trade analysis + week-over-week comparison for
    AI Journaling. Never raises out of analyze_trades/compare_analyses --
    any Groq/network/parse failure is logged and swallowed into a fallback
    dict so a flaky LLM call never breaks the sync/upload flow that
    auto-triggers this pipeline (see trade_analysis_pipeline.py).
    """

    GROQ_MODEL = "llama-3.3-70b-versatile"
    PROMPT_VERSION = "v1"

    ANALYSIS_SCHEMA = """
{
  "grade": "A/B+/B/C+/C/D/F",
  "grade_reason": "one sentence explaining the grade",
  "performance": {
    "net_pnl": number,
    "win_rate_pct": number,
    "profit_factor": number or null,
    "total_trades": number,
    "avg_trade_return": number
  },
  "psychological_profile": {
    "overall_state": "string",
    "discipline_score": number between 1 and 10,
    "revenge_trading_detected": boolean,
    "revenge_trading_evidence": "string or null",
    "overtrading_detected": boolean,
    "overtrading_evidence": "string or null",
    "fomo_detected": boolean,
    "emotional_state": "string"
  },
  "trade_behavior": {
    "trade_type": "string",
    "avg_holding_days": number,
    "stop_loss_adherence_pct": number or null,
    "best_time_observation": "string or null",
    "worst_time_observation": "string or null"
  },
  "instrument_analysis": [
    {
      "instrument": "string",
      "trades": number,
      "win_rate_pct": number,
      "avg_pnl": number,
      "verdict": "string"
    }
  ],
  "risk_management": {
    "avg_risk_per_trade_pct": number or null,
    "max_consecutive_losses": number,
    "recovery_behavior": "string",
    "worst_day_pnl": number
  },
  "actionable_insights": ["string", "string", "string"],
  "one_line_verdict": "string"
}
"""

    COMPARISON_SCHEMA = """
{
  "performance_delta": {
    "pnl_change_pct": number,
    "win_rate_change": number,
    "verdict": "Better/Worse/Same"
  },
  "psychological_change": {
    "discipline_change": "Improved/Declined/Same",
    "revenge_trading": "Resolved/Persists/New/Not detected",
    "overtrading": "Resolved/Persists/New/Not detected",
    "summary": "paragraph"
  },
  "improvements": ["string", "string", "string"],
  "still_needs_work": ["string", "string", "string"],
  "trajectory": "Improving/Declining/Stable",
  "coach_message": "personal message to trader",
  "next_week_focus": "single most important thing"
}
"""

    def __init__(self):
        from app.core.config import settings

        self.api_key = settings.GROQ_API_KEY

    def _chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        response = requests.post(
            _GROQ_CHAT_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _symbol_for(self, instrument_id, symbols_by_instrument: dict) -> str:
        return symbols_by_instrument.get(instrument_id, str(instrument_id)[:8])

    def build_trade_context(
        self,
        trades: list,
        gains: list,
        week_start: date,
        week_end: date,
    ) -> str:
        """
        Structured plain-text representation of a week's trades, fed to the
        LLM as its user-message context. Trades are matched to gains by
        (instrument_id, sell_date) so a sell trade shows the P&L it
        realized; a trade with no matching gain (an open buy, or a sell
        that produced no realized_gain row) shows "open position".
        """
        symbols_by_instrument = {
            trade.instrument_id: trade.instrument.symbol
            for trade in trades
            if getattr(trade, "instrument", None) is not None
        }

        gains_by_key: dict[tuple, list] = defaultdict(list)
        daily_pnl: dict[date, "object"] = defaultdict(lambda: 0)
        for gain in gains:
            sell_day = gain.sell_date.date() if gain.sell_date else None
            if sell_day is not None:
                gains_by_key[(gain.instrument_id, sell_day)].append(gain)
                daily_pnl[sell_day] += gain.profit_loss

        trades_by_day: dict[date, list] = defaultdict(list)
        for trade in trades:
            trades_by_day[trade.execution_time.date()].append(trade)

        total_pnl = sum(gain.profit_loss for gain in gains) if gains else 0
        lines = [
            f"WEEK: {week_start} to {week_end}",
            f"Total trades: {len(trades)}",
            f"Completed (realized) trades: {len(gains)}",
            f"Total realized P&L: {total_pnl}",
            "",
        ]

        show_detail = len(trades) <= MAX_DETAILED_TRADES

        for day in sorted(trades_by_day.keys()):
            day_trades = trades_by_day[day]
            lines.append(f"Date: {day.isoformat()}")
            if show_detail:
                lines.append("Trades:")
                for trade in day_trades:
                    symbol = self._symbol_for(trade.instrument_id, symbols_by_instrument)
                    matched = gains_by_key.get((trade.instrument_id, day), [])
                    if matched:
                        pnl = sum(gain.profit_loss for gain in matched)
                        gain_type = next(
                            (gain.gain_type for gain in matched if gain.gain_type),
                            None,
                        )
                        holding_days = matched[0].holding_days
                        pnl_str = f"{pnl} ({gain_type or 'N/A'})"
                    else:
                        holding_days = "N/A"
                        pnl_str = "open position"
                    lines.append(
                        f"  - {symbol} | {trade.trade_type.upper()} | "
                        f"qty {trade.quantity} | price {trade.price} | "
                        f"holding_days {holding_days} | P&L {pnl_str}"
                    )
            lines.append(f"Daily P&L: {daily_pnl.get(day, 0)}")
            lines.append(f"Daily trade count: {len(day_trades)}")
            lines.append("")

        return "\n".join(lines)

    def _fallback_analysis(self, base_metrics: dict) -> dict:
        return {
            "grade": "N/A",
            "grade_reason": "Analysis temporarily unavailable",
            "performance": base_metrics,
            "psychological_profile": None,
            "trade_behavior": None,
            "instrument_analysis": [],
            "risk_management": None,
            "actionable_insights": ["Connect broker for complete analysis"],
            "one_line_verdict": "Analysis unavailable",
            "analysis_unavailable": True,
        }

    def analyze_trades(
        self,
        trades: list,
        gains: list,
        week_start: date,
        week_end: date,
        base_metrics: dict,
    ) -> tuple[dict, str]:
        try:
            context = self.build_trade_context(trades, gains, week_start, week_end)
            user_prompt = (
                f"TRADE DATA:\n{context}\n\n"
                f"PRE-COMPUTED METRICS:\n{json.dumps(base_metrics, default=str, indent=2)}\n\n"
                f"Return ONLY valid JSON matching this schema:\n{self.ANALYSIS_SCHEMA}"
            )
            raw = self._chat_completion(
                system_prompt=(
                    "You are a professional trading psychology coach and "
                    "quantitative analyst specializing in Indian retail "
                    "traders on NSE/BSE. Analyze the trade history and "
                    "return ONLY valid JSON matching the schema. Be "
                    "specific — use actual trade data to support every "
                    "finding. Never give generic advice."
                ),
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=2000,
            )
            return json.loads(raw), raw
        except Exception as e:
            logger.warning(f"[FINVIGIL] Trade analysis LLM call failed: {e}")
            return self._fallback_analysis(base_metrics), ""

    def _fallback_comparison(self) -> dict:
        return {
            "performance_delta": None,
            "psychological_change": None,
            "improvements": [],
            "still_needs_work": [],
            "trajectory": "Stable",
            "coach_message": "Comparison temporarily unavailable.",
            "next_week_focus": "Keep journaling to track your progress.",
            "comparison_unavailable": True,
        }

    def compare_analyses(
        self,
        previous_analysis: dict,
        current_analysis: dict,
    ) -> tuple[dict, str]:
        try:
            user_prompt = (
                f"PREVIOUS PERIOD ANALYSIS:\n{json.dumps(previous_analysis, default=str, indent=2)}\n\n"
                f"CURRENT PERIOD ANALYSIS:\n{json.dumps(current_analysis, default=str, indent=2)}\n\n"
                f"Return ONLY valid JSON matching this schema:\n{self.COMPARISON_SCHEMA}"
            )
            raw = self._chat_completion(
                system_prompt=(
                    "You are a trading performance coach. Compare two "
                    "weekly trading analyses and identify improvements, "
                    "regressions, and trends. Return ONLY valid JSON."
                ),
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=1500,
            )
            return json.loads(raw), raw
        except Exception as e:
            logger.warning(f"[FINVIGIL] Trade comparison LLM call failed: {e}")
            return self._fallback_comparison(), ""
