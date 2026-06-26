from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class TaxExportRequest(BaseModel):
    assessment_year: str


class TransactionDetail(BaseModel):
    symbol: str
    isin: str | None
    quantity_sold: Decimal
    buy_date: datetime
    sell_date: datetime
    buy_price: Decimal
    sell_price: Decimal
    holding_days: int
    gain_type: str
    profit_loss: Decimal


class CapitalGainsSummary(BaseModel):
    total_stcg_gains: Decimal
    total_ltcg_gains: Decimal
    taxable_stcg: Decimal
    taxable_ltcg: Decimal
    stcg_tax_estimate: Decimal
    ltcg_tax_estimate: Decimal
    total_tax_estimate: Decimal
    ltcg_exemption_applied: Decimal


class CapitalGainsExportResponse(BaseModel):
    export_id: UUID
    export_type: str
    assessment_year: str
    generated_at: datetime
    user_id: UUID
    disclaimer: str
    summary: CapitalGainsSummary
    transactions: list[TransactionDetail]
