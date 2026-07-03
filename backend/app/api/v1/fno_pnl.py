from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.fno_pnl_repository import FnoPnlRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.fno_pnl import (
    FnoCalculateResponse,
    FnoOpenPositionResponse,
    FnoPnlSummaryResponse,
)
from app.services.fno_pnl_service import FnoPnlService

router = APIRouter()


def get_fno_pnl_service(
    db: Session = Depends(get_db)
) -> FnoPnlService:
    fno_pnl_repo = FnoPnlRepository(db)
    trade_repo = TradeRepository(db)
    return FnoPnlService(
        fno_pnl_repository=fno_pnl_repo,
        trade_repository=trade_repo,
    )


@router.post(
    "/fno/calculate",
    response_model=FnoCalculateResponse
)
def calculate_fno_pnl(
    user_id: UUID = Depends(get_current_user_id),
    service: FnoPnlService = Depends(get_fno_pnl_service)
):
    return service.calculate_all_fno_pnl(user_id=user_id)


@router.get(
    "/fno/pnl/",
    response_model=FnoPnlSummaryResponse
)
def get_fno_pnl(
    user_id: UUID = Depends(get_current_user_id),
    service: FnoPnlService = Depends(get_fno_pnl_service)
):
    return service.get_pnl_summary(user_id=user_id)


@router.get(
    "/fno/pnl/{assessment_year}",
    response_model=FnoPnlSummaryResponse
)
def get_fno_pnl_by_ay(
    assessment_year: str,
    user_id: UUID = Depends(get_current_user_id),
    service: FnoPnlService = Depends(get_fno_pnl_service)
):
    return service.get_pnl_summary(
        user_id=user_id,
        assessment_year=assessment_year,
    )


@router.get(
    "/fno/positions",
    response_model=list[FnoOpenPositionResponse]
)
def get_fno_positions(
    user_id: UUID = Depends(get_current_user_id),
    service: FnoPnlService = Depends(get_fno_pnl_service)
):
    return service.get_open_positions(user_id=user_id)
