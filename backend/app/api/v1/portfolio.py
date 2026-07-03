from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.schemas.portfolio import PortfolioItemResponse
from app.services.portfolio_service import PortfolioService

router = APIRouter()


def get_portfolio_service(
    db: Session = Depends(get_db)
) -> PortfolioService:
    holding_repo = HoldingLotRepository(db)
    return PortfolioService(
        holding_repository=holding_repo
    )


@router.get(
    "/portfolio/",
    response_model=list[PortfolioItemResponse]
)
def get_portfolio(
    user_id: UUID = Depends(get_current_user_id),
    service: PortfolioService = Depends(get_portfolio_service)
):
    return service.get_portfolio_summary(user_id=user_id)
