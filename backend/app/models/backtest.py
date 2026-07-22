import uuid
from datetime import date, time
from typing import List

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class BacktestStrategy(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "backtest_strategies"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Section 1: Instrument
    instrument: Mapped[str] = mapped_column(String(50), nullable=False)
    underlying_from: Mapped[str] = mapped_column(
        ENUM("cash", "futures", name="underlying_from_enum", create_type=False),
        nullable=False,
    )

    # Section 2: Entry settings
    strategy_type: Mapped[str] = mapped_column(
        ENUM("intraday", "btst", "positional", name="strategy_type_enum", create_type=False),
        nullable=False,
    )
    entry_time: Mapped[time] = mapped_column(Time, nullable=False)
    exit_time: Mapped[time] = mapped_column(Time, nullable=False)
    no_reentry_after_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    no_reentry_after_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    overall_momentum_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overall_momentum_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    overall_momentum_type: Mapped[str | None] = mapped_column(String(15), nullable=True)
    overall_momentum_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Section 3: Legwise settings
    square_off: Mapped[str] = mapped_column(
        ENUM("partial", "complete", name="square_off_enum", create_type=False),
        nullable=False,
    )
    trail_sl_to_breakeven: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trail_sl_apply_to: Mapped[str | None] = mapped_column(
        ENUM("all", "sl_legs", name="trail_apply_enum", create_type=False), nullable=True,
    )

    # Section 5: Overall SL
    overall_sl_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overall_sl_type: Mapped[str | None] = mapped_column(
        ENUM("mtm", "premium_pct", name="overall_sl_target_type_enum", create_type=False), nullable=True,
    )
    overall_sl_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    overall_sl_reentry_type: Mapped[str | None] = mapped_column(
        ENUM(
            "re_asap", "re_asap_reverse", "re_momentum", "re_momentum_reverse",
            name="reentry_type_enum", create_type=False,
        ),
        nullable=True,
    )
    overall_sl_max_reentries: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)

    # Section 5: Overall Target
    overall_target_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overall_target_type: Mapped[str | None] = mapped_column(
        ENUM("mtm", "premium_pct", name="overall_sl_target_type_enum", create_type=False), nullable=True,
    )
    overall_target_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    overall_target_reentry_type: Mapped[str | None] = mapped_column(
        ENUM(
            "re_asap", "re_asap_reverse", "re_momentum", "re_momentum_reverse",
            name="reentry_type_enum", create_type=False,
        ),
        nullable=True,
    )
    overall_target_max_reentries: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)

    # Section 5: Lock Profit
    lock_profit_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lock_profit_trigger: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    lock_profit_lock_at: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Section 5: Lock & Trail
    lock_and_trail_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lock_and_trail_trigger: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    lock_and_trail_lock_at: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    lock_and_trail_trail_by_gain: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    lock_and_trail_trail_by_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Section 5: Overall Trail SL
    overall_trail_sl_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overall_trail_sl_type: Mapped[str | None] = mapped_column(
        ENUM("mtm", "premium_pct", name="overall_sl_target_type_enum", create_type=False), nullable=True,
    )
    overall_trail_sl_gain: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    overall_trail_sl_move: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Section 6: Duration
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    legs: Mapped[List["BacktestLeg"]] = relationship(
        "BacktestLeg",
        back_populates="strategy",
        cascade="all, delete-orphan",
        order_by="BacktestLeg.leg_order",
    )
    runs: Mapped[List["BacktestRun"]] = relationship(
        "BacktestRun",
        back_populates="strategy",
        cascade="all, delete-orphan",
    )


class BacktestLeg(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "backtest_legs"

    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backtest_strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    leg_order: Mapped[int] = mapped_column(Integer, nullable=False)
    segment: Mapped[str] = mapped_column(
        ENUM("futures", "options", name="segment_enum", create_type=False),
        nullable=False,
    )
    position: Mapped[str] = mapped_column(
        ENUM("buy", "sell", name="leg_position_enum", create_type=False),
        nullable=False,
    )
    quantity_lots: Mapped[int] = mapped_column(Integer, nullable=False)

    # Options-only fields (null for futures)
    option_type: Mapped[str | None] = mapped_column(
        ENUM("CE", "PE", name="option_type_enum", create_type=False), nullable=True,
    )
    expiry: Mapped[str | None] = mapped_column(
        ENUM("weekly", "next_weekly", "monthly", "next_monthly", name="expiry_type_enum", create_type=False),
        nullable=True,
    )
    strike_type: Mapped[str | None] = mapped_column(
        ENUM(
            "atm", "otm", "itm", "premium_range", "closest_premium",
            "premium_gte", "straddle_width", "pct_of_atm",
            "synthetic_future", "atm_premium_pct",
            name="strike_type_enum", create_type=False,
        ),
        nullable=True,
    )
    strike_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    strike_value2: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Per-leg risk
    sl_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sl_type: Mapped[str | None] = mapped_column(
        ENUM("points", "percentage", "trailing", name="sl_target_type_enum", create_type=False), nullable=True,
    )
    sl_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    target_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    target_type: Mapped[str | None] = mapped_column(
        ENUM("points", "percentage", "trailing", name="sl_target_type_enum", create_type=False), nullable=True,
    )
    target_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    strategy: Mapped["BacktestStrategy"] = relationship("BacktestStrategy", back_populates="legs")


class BacktestRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "backtest_runs"

    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backtest_strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        ENUM(
            "pending", "running", "completed", "failed", "insufficient_data",
            name="backtest_status_enum", create_type=False,
        ),
        nullable=False,
        default="pending",
    )
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    strategy: Mapped["BacktestStrategy"] = relationship("BacktestStrategy", back_populates="runs")
