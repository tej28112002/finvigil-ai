from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.corporate_action_repository import CorporateActionRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.services.corporate_action_service import CorporateActionService
from app.schemas.corporate_action import (
    CorporateActionRequest,
    CorporateActionResponse,
    CorporateActionAppliedResponse,
)

router = APIRouter()


def get_corporate_action_service(
    db: Session = Depends(get_db)
) -> CorporateActionService:
    return CorporateActionService(
        corporate_action_repository=CorporateActionRepository(db),
        holding_lot_repository=HoldingLotRepository(db),
    )


@router.post(
    "/corporate-actions/apply",
    response_model=CorporateActionAppliedResponse
)
def apply_corporate_action(
    request: CorporateActionRequest,
    user_id: UUID,
    service: CorporateActionService = Depends(
        get_corporate_action_service
    )
):
    try:
        return service.apply_corporate_action(
            user_id=user_id,
            instrument_id=request.instrument_id,
            action_type=request.action_type,
            ratio=request.ratio,
            applied_at=request.applied_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/corporate-actions/",
    response_model=list[CorporateActionResponse]
)
def list_corporate_actions(
    user_id: UUID,
    service: CorporateActionService = Depends(
        get_corporate_action_service
    )
):
    return service.get_adjustments_by_user(user_id=user_id)
