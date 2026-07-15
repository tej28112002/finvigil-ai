from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.subscription import check_subscription_tier
from app.db.session import get_db
from app.repositories.monte_carlo_repository import MonteCarloRunRepository
from app.schemas.monte_carlo import MonteCarloRunRequest, MonteCarloRunResponse
from app.services.monte_carlo_service import MonteCarloService

router = APIRouter()


def get_monte_carlo_service(db: Session = Depends(get_db)) -> MonteCarloService:
    return MonteCarloService(
        monte_carlo_repository=MonteCarloRunRepository(db),
    )


@router.post("/monte-carlo/runs", response_model=MonteCarloRunResponse)
def create_run(
    request: MonteCarloRunRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    service: MonteCarloService = Depends(get_monte_carlo_service),
):
    if not check_subscription_tier(db, user_id):
        raise HTTPException(
            status_code=403,
            detail="Monte Carlo simulations require a Pro or Premium subscription.",
        )

    try:
        run = service.create_and_run(
            user_id=user_id,
            starting_value=Decimal(str(request.starting_value)),
            horizon_years=request.horizon_years,
            cpi_rate=Decimal(str(request.cpi_rate)),
            num_paths=request.num_paths,
            replay_scenario_id=request.replay_scenario_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return run


@router.get("/monte-carlo/runs", response_model=list[MonteCarloRunResponse])
def list_runs(
    user_id: UUID = Depends(get_current_user_id),
    service: MonteCarloService = Depends(get_monte_carlo_service),
):
    return service.list_runs(user_id=user_id)


@router.get("/monte-carlo/runs/{run_id}", response_model=MonteCarloRunResponse)
def get_run(
    run_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: MonteCarloService = Depends(get_monte_carlo_service),
):
    run = service.get_run(user_id=user_id, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"Monte Carlo run {run_id} not found.",
        )
    return run
