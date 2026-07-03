from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CryptoTradeIngestRequest(BaseModel):
    broker_connection_id: UUID
    broker_trade_id: str
    trade_type: str
    quantity: Decimal
    price: Decimal
    execution_time: datetime
    symbol: str
    instrument_name: str
    isin: str | None = None


class CryptoTradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    broker_connection_id: UUID
    instrument_id: UUID
    broker_trade_id: str
    trade_type: str
    quantity: Decimal
    price: Decimal
    execution_time: datetime
    idempotency_hash: str
    created_at: datetime
    updated_at: datetime


class CryptoTaxSummaryResponse(BaseModel):
    assessment_year: str
    transaction_count: int
    total_vda_gains: Decimal
    total_vda_losses: Decimal
    taxable_vda_income: Decimal
    vda_tax_rate: Decimal
    vda_tax: Decimal
    total_tds_paid: Decimal
    net_tax_payable: Decimal
    disclaimer: str = (
        "Crypto/VDA is taxed under Section 115BBH at a flat 30% (plus cess) on "
        "gains, with NO set-off of losses against any income and no carry "
        "forward. Losses are shown for reference only and are not deductible. "
        "1% TDS (Section 194S) already deducted is credited against tax. This "
        "is an estimate excluding cess/surcharge; confirm with your CA before "
        "filing."
    )
