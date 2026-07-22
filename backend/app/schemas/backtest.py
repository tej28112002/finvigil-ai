from datetime import date, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

StrikeType = Literal[
    "atm", "otm", "itm", "premium_range", "closest_premium",
    "premium_gte", "straddle_width", "pct_of_atm",
    "synthetic_future", "atm_premium_pct",
]
SlTargetType = Literal["points", "percentage", "trailing"]
OverallSlTargetType = Literal["mtm", "premium_pct"]
ReentryType = Literal["re_asap", "re_asap_reverse", "re_momentum", "re_momentum_reverse"]


class LegInput(BaseModel):
    segment: Literal["futures", "options"] = "options"
    position: Literal["buy", "sell"] = "sell"
    quantity_lots: int = 1

    # Options-only (null for futures)
    option_type: Literal["CE", "PE"] | None = None
    expiry: Literal["weekly", "next_weekly", "monthly", "next_monthly"] | None = None
    strike_type: StrikeType | None = "atm"
    strike_value: float | None = None
    strike_value2: float | None = None

    sl_enabled: bool = False
    sl_type: SlTargetType | None = None
    sl_value: float | None = None
    target_enabled: bool = False
    target_type: SlTargetType | None = None
    target_value: float | None = None


class LegResponse(LegInput):
    id: UUID
    leg_order: int

    model_config = ConfigDict(from_attributes=True)


class StrategyInput(BaseModel):
    name: str = "My Strategy"

    # Section 1: Instrument
    instrument: str = "NIFTY"
    underlying_from: Literal["cash", "futures"] = "cash"

    # Section 2: Entry settings
    strategy_type: Literal["intraday", "btst", "positional"] = "intraday"
    entry_time: time = time(9, 20)
    exit_time: time = time(15, 15)
    no_reentry_after_enabled: bool = False
    no_reentry_after_time: time | None = None
    overall_momentum_enabled: bool = False
    overall_momentum_direction: str | None = None
    overall_momentum_type: str | None = None
    overall_momentum_value: float | None = None

    # Section 3: Legwise settings
    square_off: Literal["partial", "complete"] = "partial"
    trail_sl_to_breakeven: bool = False
    trail_sl_apply_to: Literal["all", "sl_legs"] | None = "all"

    # Section 5: Overall SL
    overall_sl_enabled: bool = False
    overall_sl_type: OverallSlTargetType | None = None
    overall_sl_value: float | None = None
    overall_sl_reentry_type: ReentryType | None = None
    overall_sl_max_reentries: int | None = 1

    # Section 5: Overall Target
    overall_target_enabled: bool = False
    overall_target_type: OverallSlTargetType | None = None
    overall_target_value: float | None = None
    overall_target_reentry_type: ReentryType | None = None
    overall_target_max_reentries: int | None = 1

    # Section 5: Lock Profit
    lock_profit_enabled: bool = False
    lock_profit_trigger: float | None = None
    lock_profit_lock_at: float | None = None

    # Section 5: Lock & Trail
    lock_and_trail_enabled: bool = False
    lock_and_trail_trigger: float | None = None
    lock_and_trail_lock_at: float | None = None
    lock_and_trail_trail_by_gain: float | None = None
    lock_and_trail_trail_by_amount: float | None = None

    # Section 5: Overall Trail SL
    overall_trail_sl_enabled: bool = False
    overall_trail_sl_type: OverallSlTargetType | None = None
    overall_trail_sl_gain: float | None = None
    overall_trail_sl_move: float | None = None

    # Section 6: Duration
    start_date: date = date(2024, 1, 1)
    end_date: date = Field(default_factory=date.today)

    legs: list[LegInput] = Field(default_factory=list)


class StrategyResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str

    instrument: str
    underlying_from: str

    strategy_type: str
    entry_time: time
    exit_time: time
    no_reentry_after_enabled: bool
    no_reentry_after_time: time | None
    overall_momentum_enabled: bool
    overall_momentum_direction: str | None
    overall_momentum_type: str | None
    overall_momentum_value: float | None

    square_off: str
    trail_sl_to_breakeven: bool
    trail_sl_apply_to: str | None

    overall_sl_enabled: bool
    overall_sl_type: str | None
    overall_sl_value: float | None
    overall_sl_reentry_type: str | None
    overall_sl_max_reentries: int | None

    overall_target_enabled: bool
    overall_target_type: str | None
    overall_target_value: float | None
    overall_target_reentry_type: str | None
    overall_target_max_reentries: int | None

    lock_profit_enabled: bool
    lock_profit_trigger: float | None
    lock_profit_lock_at: float | None

    lock_and_trail_enabled: bool
    lock_and_trail_trigger: float | None
    lock_and_trail_lock_at: float | None
    lock_and_trail_trail_by_gain: float | None
    lock_and_trail_trail_by_amount: float | None

    overall_trail_sl_enabled: bool
    overall_trail_sl_type: str | None
    overall_trail_sl_gain: float | None
    overall_trail_sl_move: float | None

    start_date: date
    end_date: date

    legs: list[LegResponse]

    model_config = ConfigDict(from_attributes=True)


class RunResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    status: str
    result_json: dict | None
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)
