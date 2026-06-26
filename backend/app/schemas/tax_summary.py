from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TaxCalculationRequest(BaseModel):
    assessment_year: str


class TaxSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    assessment_year: str
    total_stcg_gains: Decimal
    total_ltcg_gains: Decimal
    stcg_tax_rate: Decimal
    ltcg_tax_rate: Decimal
    ltcg_exemption: Decimal
    taxable_stcg: Decimal
    taxable_ltcg: Decimal
    stcg_tax: Decimal
    ltcg_tax: Decimal
    total_tax_liability: Decimal
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime
    disclaimer: str = (
        "Capital gains tax estimate only. Does NOT include 4% cess, "
        "surcharge, or tax on salary, rental, or other income sources. "
        "For your complete tax liability, consult your CA."
    )
