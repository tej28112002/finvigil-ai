from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.replay_repository import (
    ReplayRunRepository,
    ReplayScenarioRepository,
)
from app.repositories.trade_repository import TradeRepository
from app.schemas.replay import (
    ReplayRunResponse,
    ReplayScenarioCreateRequest,
    ReplayScenarioResponse,
)
from app.services.replay_service import ReplayService

router = APIRouter()


def get_replay_service(db: Session = Depends(get_db)) -> ReplayService:
    return ReplayService(
        trade_repository=TradeRepository(db),
        instrument_repository=InstrumentRepository(db),
        replay_scenario_repository=ReplayScenarioRepository(db),
        replay_run_repository=ReplayRunRepository(db),
    )


@router.post("/replay/scenarios", response_model=ReplayScenarioResponse)
def create_scenario(
    request: ReplayScenarioCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: ReplayService = Depends(get_replay_service),
):
    return service.create_scenario(
        user_id=user_id,
        name=request.name,
        parameters=request.parameters.model_dump(mode="json"),
    )


@router.get("/replay/scenarios", response_model=list[ReplayScenarioResponse])
def list_scenarios(
    user_id: UUID = Depends(get_current_user_id),
    service: ReplayService = Depends(get_replay_service),
):
    return service.list_scenarios(user_id=user_id)


@router.get(
    "/replay/scenarios/{scenario_id}", response_model=ReplayScenarioResponse
)
def get_scenario(
    scenario_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: ReplayService = Depends(get_replay_service),
):
    # Ownership enforced in the query (scenario_id AND user_id) — another
    # user's scenario produces the same 404 as a nonexistent one.
    scenario = service.get_scenario(user_id=user_id, scenario_id=scenario_id)
    if not scenario:
        raise HTTPException(
            status_code=404,
            detail=f"Replay scenario {scenario_id} not found.",
        )
    return scenario


@router.delete("/replay/scenarios/{scenario_id}", status_code=204)
def delete_scenario(
    scenario_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: ReplayService = Depends(get_replay_service),
):
    deleted = service.delete_scenario(user_id=user_id, scenario_id=scenario_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Replay scenario {scenario_id} not found.",
        )


@router.post(
    "/replay/scenarios/{scenario_id}/run", response_model=ReplayRunResponse
)
def run_scenario(
    scenario_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: ReplayService = Depends(get_replay_service),
):
    try:
        run = service.run_scenario(user_id=user_id, scenario_id=scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if run is None:
        raise HTTPException(
            status_code=404,
            detail=f"Replay scenario {scenario_id} not found.",
        )
    return run


@router.get(
    "/replay/scenarios/{scenario_id}/runs", response_model=list[ReplayRunResponse]
)
def list_runs(
    scenario_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: ReplayService = Depends(get_replay_service),
):
    return service.list_runs(user_id=user_id, scenario_id=scenario_id)


@router.get("/replay/runs/{run_id}", response_model=ReplayRunResponse)
def get_run(
    run_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: ReplayService = Depends(get_replay_service),
):
    run = service.get_run(user_id=user_id, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"Replay run {run_id} not found.",
        )
    return run
