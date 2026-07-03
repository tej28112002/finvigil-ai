from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.corporate_action_repository import CorporateActionRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.reconstruction import ReconstructionResultResponse
from app.services.holding_service import HoldingLotService
from app.services.reconstruction_service import ReconstructionService

router = APIRouter()


def get_reconstruction_service(
    db: Session = Depends(get_db)
) -> ReconstructionService:
    trade_repo = TradeRepository(db)
    holding_repo = HoldingLotRepository(db)
    realized_gain_repo = RealizedGainRepository(db)
    corporate_action_repo = CorporateActionRepository(db)
    holding_service = HoldingLotService(holding_repository=holding_repo)
    return ReconstructionService(
        trade_repository=trade_repo,
        holding_lot_repository=holding_repo,
        holding_service=holding_service,
        realized_gain_repository=realized_gain_repo,
        corporate_action_repository=corporate_action_repo,
    )


@router.post(
    "/reconstruction/equity",
    response_model=ReconstructionResultResponse
)
def rebuild_equity(
    user_id: UUID = Depends(get_current_user_id),
    service: ReconstructionService = Depends(get_reconstruction_service)
):
    result = service.rebuild_equity_for_user(user_id=user_id)
    return ReconstructionResultResponse(user_id=user_id, **result)
