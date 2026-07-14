from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
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
    user_id: UUID = Depends(get_current_user_id),
    service: HoldingLotService = Depends(get_holding_service)
):
    return service.get_lots_by_user(user_id=user_id)


@router.get(
    "/holdings/{lot_id}",
    response_model=HoldingLotResponse
)
def get_holding(
    lot_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: HoldingLotService = Depends(get_holding_service)
):
    # Ownership is enforced in the query itself (filters by lot_id AND
    # user_id) — a lot that exists but belongs to another user produces the
    # exact same None as a lot that doesn't exist at all, so this 404 never
    # leaks whether the UUID is real.
    lot = service.get_lot_by_id(lot_id=lot_id, user_id=user_id)
    if not lot:
        raise HTTPException(
            status_code=404,
            detail=f"Holding lot {lot_id} not found."
        )
    return lot
