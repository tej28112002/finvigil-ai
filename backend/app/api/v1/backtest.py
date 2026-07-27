import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.backtest_repository import BacktestRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.schemas.backtest import LegInput, RunResponse, StrategyInput, StrategyResponse
from app.services.backtest_service import BacktestService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_backtest_repository(db: Session = Depends(get_db)) -> BacktestRepository:
    return BacktestRepository(db)


def get_backtest_service(db: Session = Depends(get_db)) -> BacktestService:
    return BacktestService(
        backtest_repository=BacktestRepository(db),
        realized_gain_repository=RealizedGainRepository(db),
    )


def _strategy_fields(body: StrategyInput) -> dict:
    return body.model_dump(exclude={"legs"})


def _leg_fields(leg: LegInput) -> dict:
    return leg.model_dump()


def _get_owned_strategy(
    strategy_id: UUID, user_id: UUID, repo: BacktestRepository
):
    strategy = repo.get_strategy(strategy_id, user_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.post("/backtest/strategies", response_model=StrategyResponse)
def create_strategy(
    body: StrategyInput,
    user_id: UUID = Depends(get_current_user_id),
    repo: BacktestRepository = Depends(get_backtest_repository),
):
    strategy = repo.create_strategy(user_id=user_id, **_strategy_fields(body))
    repo.upsert_legs(strategy.id, [_leg_fields(leg) for leg in body.legs])
    return repo.get_strategy(strategy.id, user_id)


@router.get("/backtest/strategies", response_model=list[StrategyResponse])
def list_strategies(
    user_id: UUID = Depends(get_current_user_id),
    repo: BacktestRepository = Depends(get_backtest_repository),
):
    return repo.list_strategies(user_id)


@router.get("/backtest/strategies/{strategy_id}", response_model=StrategyResponse)
def get_strategy(
    strategy_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repo: BacktestRepository = Depends(get_backtest_repository),
):
    return _get_owned_strategy(strategy_id, user_id, repo)


@router.put("/backtest/strategies/{strategy_id}", response_model=StrategyResponse)
def update_strategy(
    strategy_id: UUID,
    body: StrategyInput,
    user_id: UUID = Depends(get_current_user_id),
    repo: BacktestRepository = Depends(get_backtest_repository),
):
    strategy = _get_owned_strategy(strategy_id, user_id, repo)
    repo.update_strategy(strategy, **_strategy_fields(body))
    repo.upsert_legs(strategy.id, [_leg_fields(leg) for leg in body.legs])
    return repo.get_strategy(strategy.id, user_id)


@router.delete("/backtest/strategies/{strategy_id}", status_code=204)
def delete_strategy(
    strategy_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repo: BacktestRepository = Depends(get_backtest_repository),
):
    strategy = _get_owned_strategy(strategy_id, user_id, repo)
    repo.delete_strategy(strategy)


@router.post("/backtest/strategies/{strategy_id}/run", response_model=RunResponse)
def run_backtest(
    strategy_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repo: BacktestRepository = Depends(get_backtest_repository),
    service: BacktestService = Depends(get_backtest_service),
):
    strategy = _get_owned_strategy(strategy_id, user_id, repo)

    run = repo.create_run(strategy_id=strategy.id, user_id=user_id)
    try:
        result = service.run_backtest(strategy, user_id)
        run = repo.update_run(run, status=result.get("status", "completed"), result_json=result)
    except Exception as e:
        logger.warning(f"[FINVIGIL] backtest run failed: {type(e).__name__}: {e}")
        run = repo.update_run(run, status="failed", error=str(e))
    return run


@router.get("/backtest/strategies/{strategy_id}/runs", response_model=list[RunResponse])
def list_runs(
    strategy_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repo: BacktestRepository = Depends(get_backtest_repository),
):
    _get_owned_strategy(strategy_id, user_id, repo)
    return repo.list_runs(strategy_id, user_id)
