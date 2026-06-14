from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.schemas.holding import HoldingLotResponse
from app.services.holding_service import HoldingLotService

router = APIRouter()


def get_holding_service(
    db: Session = Depends(get_db)
) -> HoldingLotService:
    holding_repo = HoldingLotRepository(db)
    return HoldingLotService(
        holding_repository=holding_repo
    )


@router.get(
    "/holdings/",
    response_model=list[HoldingLotResponse]
)
def list_holdings(
    user_id: UUID,
    service: HoldingLotService = Depends(get_holding_service)
):
    return service.get_lots_by_user(user_id=user_id)


@router.get(
    "/holdings/{lot_id}",
    response_model=HoldingLotResponse
)
def get_holding(
    lot_id: UUID,
    service: HoldingLotService = Depends(get_holding_service)
):
    lot = service.get_lot_by_id(lot_id=lot_id)
    if not lot:
        raise HTTPException(
            status_code=404,
            detail=f"Holding lot {lot_id} not found."
        )
    return lot
