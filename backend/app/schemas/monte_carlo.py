from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

_MC_DISCLAIMER = (
    "This Monte Carlo simulation uses Geometric Brownian Motion with "
    "hard-coded 25% annual volatility and a user-specified CPI drift. "
    "It is for educational purposes only and does not constitute "
    "financial advice. Past performance does not predict future results. "
    "Consult your CA before making investment decisions."
)


class MonteCarloRunRequest(BaseModel):
    starting_value: Decimal
    horizon_years: int = Field(ge=1, le=30)
    cpi_rate: Decimal = Decimal("0.05")
    num_paths: int = Field(default=1000, ge=100, le=5000)
    replay_scenario_id: Optional[UUID] = None


class PercentileBand(BaseModel):
    year: int
    p5: str
    p25: str
    p50: str
    p75: str
    p95: str


class FinalDistribution(BaseModel):
    p5: str
    p25: str
    p50: str
    p75: str
    p95: str
    mean: str


class ParametersUsed(BaseModel):
    starting_value: str
    horizon_years: int
    annual_drift: str
    annual_volatility: str
    num_paths: int


class MonteCarloResultData(BaseModel):
    bands: list[PercentileBand]
    final_distribution: FinalDistribution
    parameters_used: ParametersUsed
    disclaimer: str = _MC_DISCLAIMER


class MonteCarloRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    replay_scenario_id: Optional[UUID]
    parameters: dict
    status: str
    result_data: Optional[MonteCarloResultData]
    created_at: datetime
    updated_at: datetime
