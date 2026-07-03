from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

_FNO_DISCLAIMER = (
    "F&O P&L is treated as business income (PGBP), not capital gains. "
    "Intraday F&O is speculative business income; positional F&O is "
    "non-speculative business income. This is an estimate to assist "
    "ITR-3 preparation only — the applicable tax rate, turnover "
    "calculation, and tax-audit requirements must be determined by your CA."
)


class FnoPnlEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    instrument_id: UUID
    buy_trade_id: UUID | None
    sell_trade_id: UUID
    symbol: str
    quantity: Decimal
    buy_price: Decimal
    sell_price: Decimal
    buy_time: datetime | None
    sell_time: datetime
    profit_loss: Decimal
    is_intraday: bool
    assessment_year: str
    created_at: datetime
    updated_at: datetime


class FnoOpenPositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    instrument_id: UUID
    symbol: str
    open_quantity: Decimal
    avg_buy_price: Decimal


class FnoPnlSummaryResponse(BaseModel):
    total_pnl: Decimal
    intraday_pnl: Decimal
    positional_pnl: Decimal
    realized_entry_count: int
    open_positions: list[FnoOpenPositionResponse]
    entries: list[FnoPnlEntryResponse]
    disclaimer: str = _FNO_DISCLAIMER


class FnoCalculateResponse(BaseModel):
    instruments_processed: int
    realized_entries_created: int
    open_positions_count: int
    total_pnl: Decimal
