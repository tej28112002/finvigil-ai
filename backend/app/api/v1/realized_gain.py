from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.schemas.realized_gain import RealizedGainResponse
from app.services.realized_gain_service import RealizedGainService

router = APIRouter()


def get_realized_gain_service(
    db: Session = Depends(get_db)
) -> RealizedGainService:
    realized_gain_repo = RealizedGainRepository(db)
    return RealizedGainService(
        realized_gain_repository=realized_gain_repo
    )


@router.get(
    "/realized-gains/",
    response_model=list[RealizedGainResponse]
)
def list_realized_gains(
    user_id: UUID = Depends(get_current_user_id),
    service: RealizedGainService = Depends(get_realized_gain_service)
):
    return service.get_gains_by_user(user_id=user_id)


@router.get(
    "/realized-gains/instrument/{instrument_id}",
    response_model=list[RealizedGainResponse]
)
def list_realized_gains_by_instrument(
    instrument_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: RealizedGainService = Depends(get_realized_gain_service)
):
    return service.get_gains_by_instrument(
        user_id=user_id,
        instrument_id=instrument_id
    )


@router.get(
    "/realized-gains/trade/{sell_trade_id}",
    response_model=list[RealizedGainResponse]
)
def list_realized_gains_by_trade(
    sell_trade_id: UUID,
    service: RealizedGainService = Depends(get_realized_gain_service),
    user_id: UUID = Depends(get_current_user_id),
):
    # Ownership enforced in the query (sell_trade_id AND user_id) — another
    # user's sell_trade_id now returns [] instead of their real gains. No
    # 404 branch here (there never was one): this is a filtered-list
    # endpoint, and an empty match was already a normal 200 [] response —
    # the fix is that a cross-user ID can no longer produce someone else's
    # data, not a new not-found status.
    return service.get_gains_by_sell_trade(
        sell_trade_id=sell_trade_id,
        user_id=user_id,
    )
