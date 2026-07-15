import math
import random
from decimal import Decimal
from typing import Optional
from uuid import UUID

from app.models.monte_carlo_run import MonteCarloRun
from app.repositories.monte_carlo_repository import MonteCarloRunRepository

ZERO = Decimal("0")

DEFAULT_NUM_PATHS = 1000
DEFAULT_CPI_RATE = Decimal("0.05")
DEFAULT_ANNUAL_VOLATILITY = Decimal("0.25")
PERCENTILES = (5, 25, 50, 75, 95)

_MC_DISCLAIMER = (
    "This Monte Carlo simulation uses Geometric Brownian Motion with "
    "hard-coded 25% annual volatility and a user-specified CPI drift. "
    "It is for educational purposes only and does not constitute "
    "financial advice. Past performance does not predict future results. "
    "Consult your CA before making investment decisions."
)


class MonteCarloService:
    def __init__(
        self,
        monte_carlo_repository: MonteCarloRunRepository,
    ):
        self.monte_carlo_repository = monte_carlo_repository

    def create_and_run(
        self,
        user_id: UUID,
        starting_value: Decimal,
        horizon_years: int,
        cpi_rate: Decimal = DEFAULT_CPI_RATE,
        num_paths: int = DEFAULT_NUM_PATHS,
        replay_scenario_id: Optional[UUID] = None,
    ) -> MonteCarloRun:
        if starting_value <= ZERO:
            raise ValueError("Starting value must be positive.")
        if horizon_years < 1 or horizon_years > 30:
            raise ValueError("Horizon must be between 1 and 30 years.")
        if num_paths < 100 or num_paths > 5000:
            raise ValueError("Number of paths must be between 100 and 5000.")

        parameters = {
            "starting_value": str(starting_value),
            "horizon_years": horizon_years,
            "cpi_rate": str(cpi_rate),
            "annual_volatility": str(DEFAULT_ANNUAL_VOLATILITY),
            "num_paths": num_paths,
        }

        result_data = self._run_gbm(
            starting_value=float(starting_value),
            horizon_years=horizon_years,
            annual_drift=float(cpi_rate),
            annual_vol=float(DEFAULT_ANNUAL_VOLATILITY),
            num_paths=num_paths,
        )

        run = self.monte_carlo_repository.create_run(
            user_id=user_id,
            replay_scenario_id=replay_scenario_id,
            parameters=parameters,
            status="done",
            result_data=result_data,
        )
        return run

    def get_run(self, user_id: UUID, run_id: UUID) -> MonteCarloRun | None:
        return self.monte_carlo_repository.get_by_id_and_user(
            run_id=run_id,
            user_id=user_id,
        )

    def list_runs(self, user_id: UUID) -> list[MonteCarloRun]:
        return self.monte_carlo_repository.get_by_user(user_id=user_id)

    @staticmethod
    def _run_gbm(
        starting_value: float,
        horizon_years: int,
        annual_drift: float,
        annual_vol: float,
        num_paths: int,
    ) -> dict:
        dt = 1.0
        drift_per_step = (annual_drift - 0.5 * annual_vol ** 2) * dt
        vol_per_step = annual_vol * math.sqrt(dt)

        all_paths: list[list[float]] = []

        for _ in range(num_paths):
            value = starting_value
            path = [value]
            for _ in range(horizon_years):
                z = random.gauss(0, 1)
                value *= math.exp(drift_per_step + vol_per_step * z)
                path.append(value)
            all_paths.append(path)

        bands: list[dict] = []
        for year in range(horizon_years + 1):
            values_at_year = sorted(p[year] for p in all_paths)
            n = len(values_at_year)
            percentile_values = {}
            for pct in PERCENTILES:
                idx = int(n * pct / 100)
                idx = min(idx, n - 1)
                percentile_values[f"p{pct}"] = str(
                    Decimal(str(round(values_at_year[idx], 2)))
                )
            bands.append({"year": year, **percentile_values})

        final_values = sorted(p[horizon_years] for p in all_paths)
        n = len(final_values)
        final_summary = {}
        for pct in PERCENTILES:
            idx = min(int(n * pct / 100), n - 1)
            final_summary[f"p{pct}"] = str(
                Decimal(str(round(final_values[idx], 2)))
            )
        final_summary["mean"] = str(
            Decimal(str(round(sum(final_values) / n, 2)))
        )

        return {
            "bands": bands,
            "final_distribution": final_summary,
            "parameters_used": {
                "starting_value": str(Decimal(str(round(starting_value, 2)))),
                "horizon_years": horizon_years,
                "annual_drift": str(annual_drift),
                "annual_volatility": str(annual_vol),
                "num_paths": num_paths,
            },
            "disclaimer": _MC_DISCLAIMER,
        }
