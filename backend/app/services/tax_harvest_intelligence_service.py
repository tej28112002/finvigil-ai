"""
Tax Harvesting Intelligence — six rule-based strategies for legally
minimizing capital gains tax under Indian tax law (equity, current FY).

Every strategy is a plain function of realized_gains and open holding_lots
already in the DB — no external API calls, no live prices. Where a
strategy would need a live price (e.g. "sell this lot to book LTCG"), it
says so explicitly via requires_live_price rather than guessing.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.realized_gain_repository import RealizedGainRepository

logger = logging.getLogger(__name__)

LTCG_EXEMPTION_LIMIT = Decimal("125000")  # Rs 1,25,000 per FY
LTCG_RATE = Decimal("0.125")  # 12.5%
STCG_RATE = Decimal("0.20")  # 20%
LTCG_HOLDING_DAYS = 365  # proxy for "more than 12 months"


def _get_current_fy() -> tuple[date, date]:
    """Returns (fy_start, fy_end) for the current Indian FY (April 1 to
    March 31), computed from today's date rather than hardcoded — a
    hardcoded FY goes stale the moment the calendar crosses into the next
    one and starts reporting a negative "days until FY end"."""
    today = date.today()
    if today.month >= 4:
        # April onwards = new FY has started
        fy_start = date(today.year, 4, 1)
        fy_end = date(today.year + 1, 3, 31)
    else:
        # Jan-March = still in the FY that started the previous year
        fy_start = date(today.year - 1, 4, 1)
        fy_end = date(today.year, 3, 31)
    return fy_start, fy_end


class TaxHarvestingIntelligenceService:
    def __init__(
        self,
        realized_gain_repository: RealizedGainRepository,
        holding_lot_repository: HoldingLotRepository,
        dashboard_repository: DashboardRepository,
    ):
        self.realized_gain_repository = realized_gain_repository
        self.holding_lot_repository = holding_lot_repository
        self.dashboard_repository = dashboard_repository

    # ── core data ────────────────────────────────────────────────────────

    def _get_current_fy_realized_gains(self, user_id: UUID) -> list:
        """All realized gains with sell_date in the current FY (April 1 to
        March 31, computed from today's date)."""
        fy_start, fy_end = _get_current_fy()
        all_gains = self.realized_gain_repository.get_by_user(user_id)
        return [
            g for g in all_gains
            if fy_start <= g.sell_date.date() <= fy_end
        ]

    def _compute_fy_summary(self, fy_gains: list) -> dict:
        ltcg_gains = sum(
            Decimal(str(g.profit_loss)) for g in fy_gains
            if g.gain_type == "LTCG" and g.profit_loss > 0
        )
        stcg_gains = sum(
            Decimal(str(g.profit_loss)) for g in fy_gains
            if g.gain_type == "STCG" and g.profit_loss > 0
        )
        ltcg_losses = abs(sum(
            Decimal(str(g.profit_loss)) for g in fy_gains
            if g.gain_type == "LTCG" and g.profit_loss < 0
        ))
        stcg_losses = abs(sum(
            Decimal(str(g.profit_loss)) for g in fy_gains
            if g.gain_type == "STCG" and g.profit_loss < 0
        ))

        # Section 70 set-off: STCG losses offset STCG first, then LTCG.
        # LTCG losses offset LTCG only.
        net_stcg = max(Decimal("0"), stcg_gains - stcg_losses)
        stcg_loss_remainder = max(Decimal("0"), stcg_losses - stcg_gains)

        net_ltcg = max(
            Decimal("0"),
            ltcg_gains - ltcg_losses - stcg_loss_remainder,
        )

        ltcg_exemption_remaining = max(
            Decimal("0"), LTCG_EXEMPTION_LIMIT - ltcg_gains
        )

        taxable_ltcg = max(Decimal("0"), net_ltcg - ltcg_exemption_remaining)
        ltcg_tax = taxable_ltcg * LTCG_RATE
        stcg_tax = net_stcg * STCG_RATE

        return {
            "total_ltcg_booked": float(ltcg_gains),
            "total_stcg_booked": float(stcg_gains),
            "total_ltcg_losses": float(ltcg_losses),
            "total_stcg_losses": float(stcg_losses),
            "ltcg_exemption_remaining": float(ltcg_exemption_remaining),
            "net_ltcg": float(net_ltcg),
            "net_stcg": float(net_stcg),
            "current_ltcg_tax": float(ltcg_tax),
            "current_stcg_tax": float(stcg_tax),
            "total_tax_liability": float(ltcg_tax + stcg_tax),
        }

    # ── strategy 1: LTCG exemption harvesting ───────────────────────────

    def strategy_ltcg_exemption_harvest(
        self, user_id: UUID, fy_summary: dict
    ) -> dict | None:
        exemption_remaining = Decimal(str(fy_summary["ltcg_exemption_remaining"]))

        if exemption_remaining <= 0:
            return None

        _, fy_end = _get_current_fy()
        all_lots = self.holding_lot_repository.get_active_lots_by_user(user_id)
        today = date.today()
        ltcg_lots = []
        for lot in all_lots:
            days_held = (today - lot.buy_date.date()).days
            if days_held > LTCG_HOLDING_DAYS:
                ltcg_lots.append({
                    "lot_id": str(lot.id),
                    "symbol": lot.instrument.symbol if lot.instrument else "Unknown",
                    "instrument_type": lot.instrument.instrument_type if lot.instrument else "equity",
                    "buy_date": str(lot.buy_date.date()),
                    "buy_price": float(lot.buy_price),
                    "quantity_remaining": float(lot.quantity_remaining),
                    "holding_days": days_held,
                    "cost_basis_total": float(
                        Decimal(str(lot.buy_price)) * Decimal(str(lot.quantity_remaining))
                    ),
                    "qualifies_for_ltcg": True,
                })

        if not ltcg_lots:
            return None

        tax_saving_estimate = float(exemption_remaining * LTCG_RATE)

        return {
            "strategy_id": "ltcg_exemption_harvest",
            "title": "Use Your Annual ₹1,25,000 Tax-Free LTCG Limit",
            "subtitle": (
                f"Book up to ₹{int(exemption_remaining):,} in profits this FY with ZERO tax"
            ),
            "priority": "HIGH",
            "priority_color": "success",
            "tax_saving_estimate": tax_saving_estimate,
            "exemption_remaining": float(exemption_remaining),
            "applicable_lots": ltcg_lots,
            "instructions": [
                f"Sell long-term holdings (held > 1 year) to book up to "
                f"₹{int(exemption_remaining):,} in profits.",
                "This profit is completely TAX-FREE under Section 112A as it "
                "falls within your annual ₹1,25,000 LTCG exemption.",
                "Immediately rebuy the same shares — your cost basis resets to "
                "today's higher price permanently.",
                f"Potential tax saving: ₹{int(tax_saving_estimate):,} "
                f"(12.5% of exemption amount).",
                "Do this before March 31 every financial year without fail.",
            ],
            "legal_basis": "Section 112A, Income Tax Act 1961",
            "requires_live_price": True,
            "disclaimer": (
                "Actual tax saving depends on current market price. Connect "
                "your broker for live unrealized P&L calculation."
            ),
            "fy_deadline": str(fy_end),
            "days_until_fy_end": (fy_end - today).days,
        }

    # ── strategy 2: holding period optimizer (STCG -> LTCG) ─────────────

    def strategy_holding_period_optimizer(self, user_id: UUID) -> list[dict]:
        all_lots = self.holding_lot_repository.get_active_lots_by_user(user_id)
        today = date.today()
        alerts = []

        for lot in all_lots:
            days_held = (today - lot.buy_date.date()).days
            days_to_ltcg = LTCG_HOLDING_DAYS - days_held

            # Alert window: 1 to 90 days away from the LTCG threshold — a
            # lot that's about to cross (a handful of days out) is exactly
            # when this alert is most actionable, so the floor stays low
            # rather than excluding the most urgent cases.
            if 1 <= days_to_ltcg <= 90:
                cost_basis = Decimal(str(lot.buy_price)) * Decimal(str(lot.quantity_remaining))
                # No live price, so this is illustrative only: if the lot had
                # a 20% gain, saving = (cost_basis * 0.20) * 0.075.
                illustrative_saving = float(cost_basis * Decimal("0.015"))
                symbol = lot.instrument.symbol if lot.instrument else "Unknown"
                ltcg_date = lot.buy_date.date() + timedelta(days=LTCG_HOLDING_DAYS)

                alerts.append({
                    "strategy_id": "holding_period_optimizer",
                    "lot_id": str(lot.id),
                    "title": f"Hold {days_to_ltcg} More Days — Save 7.5% Tax",
                    "subtitle": f"{symbol} qualifies for LTCG on {ltcg_date}",
                    # HIGH tracks "urgent" (<=14 days) rather than the wider
                    # 10-90 day alert window, so an alert that just crossed
                    # into the window doesn't read as equally pressing as
                    # one about to expire.
                    "priority": "HIGH" if days_to_ltcg <= 14 else "MEDIUM",
                    "priority_color": "success" if days_to_ltcg <= 14 else "warning",
                    "symbol": symbol,
                    "buy_date": str(lot.buy_date.date()),
                    "buy_price": float(lot.buy_price),
                    "quantity": float(lot.quantity_remaining),
                    "days_held": days_held,
                    "days_to_ltcg": days_to_ltcg,
                    "ltcg_date": str(ltcg_date),
                    "cost_basis_total": float(cost_basis),
                    "illustrative_tax_saving": illustrative_saving,
                    "instructions": [
                        f"Do NOT sell {symbol} for at least {days_to_ltcg} more days.",
                        f"After {ltcg_date}, your gains qualify as LTCG taxed at "
                        f"12.5% (instead of STCG at 20%).",
                        "Tax rate reduction: 20% → 12.5% (saving 7.5% on gains).",
                        "If your gains are under ₹1,25,000, LTCG will be "
                        "completely tax-free.",
                        f"Set a calendar reminder for {ltcg_date + timedelta(days=1)}.",
                    ],
                    "legal_basis": (
                        "Section 111A (STCG 20%) vs Section 112A (LTCG 12.5%), "
                        "holding period > 12 months"
                    ),
                    "urgent": days_to_ltcg <= 14,
                })

        alerts.sort(key=lambda x: x["days_to_ltcg"])
        return alerts

    # ── strategy 3: tax loss harvesting ─────────────────────────────────

    def strategy_tax_loss_harvest(self, user_id: UUID, fy_summary: dict) -> dict | None:
        net_stcg = Decimal(str(fy_summary["net_stcg"]))
        net_ltcg = Decimal(str(fy_summary["net_ltcg"]))
        total_gains = net_stcg + net_ltcg

        if total_gains <= 0:
            return None

        current_tax = Decimal(str(fy_summary["total_tax_liability"]))
        if current_tax <= 0:
            return None

        all_lots = self.holding_lot_repository.get_active_lots_by_user(user_id)
        _, fy_end = _get_current_fy()

        return {
            "strategy_id": "tax_loss_harvest",
            "title": "Offset Your Gains with Harvested Losses",
            "subtitle": (
                f"You have ₹{int(current_tax):,} in estimated tax liability. "
                f"Losses can reduce this to ₹0."
            ),
            "priority": "HIGH",
            "priority_color": "success",
            "current_tax_liability": float(current_tax),
            "current_net_stcg": float(net_stcg),
            "current_net_ltcg": float(net_ltcg),
            "loss_needed_to_zero_tax": float(current_tax / STCG_RATE),
            "open_lots_count": len(all_lots),
            "instructions": [
                f"You have ₹{int(current_tax):,} in estimated capital gains tax this FY.",
                "Identify holdings that are currently at a loss (current price "
                "below your buy price).",
                "Sell those loss-making positions before March 31. The realized "
                "loss directly offsets your gains.",
                "STCG losses offset STCG gains first (saves 20% per Rs), then "
                "LTCG gains (saves 12.5% per Rs).",
                "You can rebuy the same stock immediately — India has no 'wash "
                "sale' rule unlike the US.",
                "Recommended: Wait 30 days before rebuying to avoid any IT "
                "department scrutiny on the transaction.",
                "Connect your broker for live prices to see exactly which "
                "holdings are at a loss right now.",
            ],
            "legal_basis": (
                "Section 70, Income Tax Act — Capital losses can be set off "
                "against capital gains in the same FY"
            ),
            "requires_live_price": True,
            "set_off_rules": {
                "stcg_loss_vs_stcg_gain": True,
                "stcg_loss_vs_ltcg_gain": True,
                "ltcg_loss_vs_stcg_gain": False,
                "ltcg_loss_vs_ltcg_gain": True,
            },
            "fy_deadline": str(fy_end),
        }

    # ── strategy 4: financial year boundary splitting ───────────────────

    def strategy_fy_boundary_split(self, user_id: UUID, fy_summary: dict) -> dict | None:
        today = date.today()
        _, fy_end = _get_current_fy()
        days_until_fy_end = (fy_end - today).days

        # Most relevant in Feb-March (within 90 days of FY end). A negative
        # value means the FY has already ended (stale computation, or this
        # ran right at the rollover) -- not applicable either way.
        if days_until_fy_end < 0 or days_until_fy_end > 90:
            return None

        exemption_remaining = Decimal(str(fy_summary["ltcg_exemption_remaining"]))
        next_fy_exemption = LTCG_EXEMPTION_LIMIT
        total_available = exemption_remaining + next_fy_exemption

        return {
            "strategy_id": "fy_boundary_split",
            "title": "Split Your Sale Across FY Boundary — Save Double Exemption",
            "subtitle": (
                f"FY ends in {days_until_fy_end} days. Use "
                f"₹{int(exemption_remaining):,} this FY + "
                f"₹{int(next_fy_exemption):,} next FY = "
                f"₹{int(total_available):,} tax-free."
            ),
            "priority": "HIGH" if days_until_fy_end <= 45 else "MEDIUM",
            "priority_color": "warning",
            "days_until_fy_end": days_until_fy_end,
            "fy_deadline": str(fy_end),
            "exemption_this_fy": float(exemption_remaining),
            "exemption_next_fy": float(next_fy_exemption),
            "total_tax_free_gains_possible": float(total_available),
            "tax_saving_estimate": float(total_available * LTCG_RATE),
            "instructions": [
                f"The financial year ends on March 31. You have "
                f"{days_until_fy_end} days left.",
                f"This FY, you can still book ₹{int(exemption_remaining):,} more "
                f"in LTCG tax-free (your remaining exemption).",
                "After April 1, a fresh ₹1,25,000 exemption becomes available "
                "for the new FY.",
                "Strategy: Sell partial holdings before March 31 to use this "
                "FY's exemption, then sell the remainder after April 1.",
                "Example: If you have ₹2,50,000 unrealized LTCG — sell "
                "₹1,25,000 worth before March 31, and the remaining "
                "₹1,25,000 after April 1 → ZERO tax on the full ₹2,50,000.",
                "This requires planning with your broker's trade execution — "
                "ensure the sale settles before March 31.",
            ],
            "legal_basis": (
                "Section 112A — ₹1,25,000 LTCG exemption is per assessment "
                "year and resets on April 1"
            ),
            "requires_live_price": True,
        }

    # ── strategy 5: loss carry forward planning ─────────────────────────

    def strategy_loss_carry_forward(self, user_id: UUID, fy_summary: dict) -> dict | None:
        total_ltcg_losses = Decimal(str(fy_summary["total_ltcg_losses"]))
        total_stcg_losses = Decimal(str(fy_summary["total_stcg_losses"]))
        total_gains = (
            Decimal(str(fy_summary["total_ltcg_booked"]))
            + Decimal(str(fy_summary["total_stcg_booked"]))
        )
        total_losses = total_ltcg_losses + total_stcg_losses

        net_loss_available = max(Decimal("0"), total_losses - total_gains)

        if net_loss_available <= 0:
            return None

        future_tax_saving = float(net_loss_available * STCG_RATE)

        return {
            "strategy_id": "loss_carry_forward",
            "title": "Carry Forward Your Losses — 8-Year Tax Credit",
            "subtitle": (
                f"₹{int(net_loss_available):,} in unabsorbed losses can offset "
                f"future gains for 8 years."
            ),
            "priority": "MEDIUM",
            "priority_color": "warning",
            "unabsorbed_loss": float(net_loss_available),
            "future_tax_saving_estimate": future_tax_saving,
            "instructions": [
                f"You have ₹{int(net_loss_available):,} in net capital losses "
                f"that couldn't be offset against gains this FY.",
                "These losses can be CARRIED FORWARD for up to 8 Assessment "
                "Years (until AY 2033-34).",
                "CRITICAL: You MUST file your ITR on time (before the due "
                "date, typically July 31) to claim carry forward.",
                "If you miss the ITR deadline, you lose the right to carry "
                "forward these losses permanently.",
                "Next year, these losses will automatically offset your "
                "capital gains, reducing your tax liability.",
                f"Estimated future tax benefit: ₹{int(future_tax_saving):,}",
            ],
            "legal_basis": (
                "Section 74, Income Tax Act — Capital losses can be carried "
                "forward for 8 assessment years if ITR is filed on time"
            ),
            "itr_deadline_reminder": True,
        }

    # ── strategy 6: set-off priority optimizer ──────────────────────────

    def strategy_setoff_optimizer(self, user_id: UUID, fy_summary: dict) -> dict | None:
        stcg_gains = Decimal(str(fy_summary["total_stcg_booked"]))
        ltcg_gains = Decimal(str(fy_summary["total_ltcg_booked"]))
        stcg_losses = Decimal(str(fy_summary["total_stcg_losses"]))
        ltcg_losses = Decimal(str(fy_summary["total_ltcg_losses"]))

        if (stcg_losses + ltcg_losses) == 0:
            return None
        if (stcg_gains + ltcg_gains) == 0:
            return None

        # Optimal: STCG losses offset STCG first, then LTCG.
        stcg_loss_vs_stcg = min(stcg_losses, stcg_gains)
        stcg_loss_remainder = stcg_losses - stcg_loss_vs_stcg
        stcg_loss_vs_ltcg = min(stcg_loss_remainder, ltcg_gains)
        ltcg_loss_vs_ltcg = min(ltcg_losses, ltcg_gains - stcg_loss_vs_ltcg)

        net_stcg = max(Decimal("0"), stcg_gains - stcg_loss_vs_stcg)
        net_ltcg = max(
            Decimal("0"), ltcg_gains - stcg_loss_vs_ltcg - ltcg_loss_vs_ltcg
        )

        optimal_stcg_tax = net_stcg * STCG_RATE
        optimal_ltcg_tax = max(Decimal("0"), net_ltcg - LTCG_EXEMPTION_LIMIT) * LTCG_RATE
        optimal_total = optimal_stcg_tax + optimal_ltcg_tax

        return {
            "strategy_id": "setoff_optimizer",
            "title": "Optimal Loss Set-off Order",
            "subtitle": "Use losses in the right order to maximize tax savings",
            "priority": "MEDIUM",
            "priority_color": "success",
            "stcg_gains": float(stcg_gains),
            "ltcg_gains": float(ltcg_gains),
            "stcg_losses": float(stcg_losses),
            "ltcg_losses": float(ltcg_losses),
            "optimal_tax": float(optimal_total),
            "set_off_breakdown": {
                "stcg_loss_against_stcg": float(stcg_loss_vs_stcg),
                "stcg_loss_against_ltcg": float(stcg_loss_vs_ltcg),
                "ltcg_loss_against_ltcg": float(ltcg_loss_vs_ltcg),
            },
            "instructions": [
                "Set-off order (most tax-efficient, highest to lowest):",
                "1. STCG losses vs STCG gains (saves 20% per Rs offset)",
                "2. Remaining STCG losses vs LTCG gains (saves 12.5% per Rs)",
                "3. LTCG losses vs LTCG gains (saves 12.5% per Rs)",
                "IMPORTANT: LTCG losses CANNOT offset STCG gains by law.",
                "This order is automatically applied in our tax computation.",
            ],
            "legal_basis": "Section 70, Income Tax Act — set-off rules",
        }

    # ── combined ─────────────────────────────────────────────────────────

    def compute_all_strategies(self, user_id: UUID) -> dict:
        fy_gains = self._get_current_fy_realized_gains(user_id)
        fy_summary = self._compute_fy_summary(fy_gains)

        strategies: list[dict] = []

        for method, args in [
            (self.strategy_ltcg_exemption_harvest, [fy_summary]),
            (self.strategy_fy_boundary_split, [fy_summary]),
            (self.strategy_tax_loss_harvest, [fy_summary]),
            (self.strategy_loss_carry_forward, [fy_summary]),
            (self.strategy_setoff_optimizer, [fy_summary]),
        ]:
            try:
                result = method(user_id, *args)
                if result is not None:
                    if isinstance(result, list):
                        strategies.extend(result)
                    else:
                        strategies.append(result)
            except Exception as e:
                logger.warning(
                    f"[FINVIGIL] harvest strategy failed: {type(e).__name__}: {e}"
                )

        try:
            hp_alerts = self.strategy_holding_period_optimizer(user_id)
            strategies.extend(hp_alerts)
        except Exception as e:
            logger.warning(
                f"[FINVIGIL] holding period strategy failed: {type(e).__name__}: {e}"
            )

        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        strategies.sort(key=lambda s: priority_order.get(s.get("priority", "LOW"), 2))

        fy_start, fy_end = _get_current_fy()
        fy_label = f"FY {fy_start.year}-{str(fy_end.year)[2:]} (AY {fy_end.year}-{str(fy_end.year + 1)[2:]})"
        assessment_year = f"AY {fy_end.year}-{str(fy_end.year + 1)[2:]}"

        return {
            "fy_summary": fy_summary,
            "strategies": strategies,
            "total_strategies": len(strategies),
            "potential_tax_saving": sum(
                s.get("tax_saving_estimate", 0) for s in strategies
            ),
            "current_fy": fy_label,
            "assessment_year": assessment_year,
            "rates": {
                "stcg_rate_pct": 20.0,
                "ltcg_rate_pct": 12.5,
                "ltcg_exemption": 125000,
            },
            "disclaimer": (
                "Tax estimates are indicative only. Consult your CA before "
                "executing any transaction. FinVigil does not execute trades — "
                "all actions must be performed manually through your broker."
            ),
        }
