from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

_REPLAY_DISCLAIMER = (
    "Portfolio Replay reconstructs invested capital and realized P&L from "
    "your trade history as of the selected date using FIFO cost basis. It "
    "does not apply historical or live market prices, so it is not a "
    "mark-to-market valuation as of that date. What-if trades are "
    "hypothetical and are never written to your real holdings. Not "
    "financial advice — consult your CA."
)


class WhatIfTrade(BaseModel):
    symbol: str
    trade_type: Literal["buy", "sell"]
    quantity: Decimal
    price: Decimal
    execution_time: datetime


class ReplayParameters(BaseModel):
    as_of_date: datetime
    what_if_trades: list[WhatIfTrade] = []


class ReplayScenarioCreateRequest(BaseModel):
    name: str
    parameters: ReplayParameters


class ReplayScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    parameters: ReplayParameters
    created_at: datetime
    updated_at: datetime


class ReplayHoldingSnapshot(BaseModel):
    instrument_id: UUID
    symbol: str
    quantity: Decimal
    avg_buy_price: Decimal
    invested_value: Decimal


class ReplayResultData(BaseModel):
    as_of_date: datetime
    holdings: list[ReplayHoldingSnapshot]
    total_invested: Decimal
    realized_pnl_to_date: Decimal
    trades_replayed: int
    what_if_trades_applied: int
    disclaimer: str = _REPLAY_DISCLAIMER


class ReplayRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    replay_scenario_id: UUID
    result_data: ReplayResultData
    created_at: datetime
