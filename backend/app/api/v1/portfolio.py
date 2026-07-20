from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.portfolio import PortfolioItemResponse, XirrResponse
from app.services.nifty_service import NiftyService
from app.services.portfolio_service import PortfolioService
from app.services.xirr_service import XirrService

router = APIRouter()


def get_portfolio_service(
    db: Session = Depends(get_db)
) -> PortfolioService:
    holding_repo = HoldingLotRepository(db)
    return PortfolioService(
        holding_repository=holding_repo
    )


def get_xirr_service(db: Session = Depends(get_db)) -> XirrService:
    return XirrService(
        trade_repository=TradeRepository(db),
        holding_repository=HoldingLotRepository(db),
        dashboard_repository=DashboardRepository(db),
        nifty_service=NiftyService(),
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


@router.get("/portfolio/xirr", response_model=XirrResponse)
def get_portfolio_xirr(
    user_id: UUID = Depends(get_current_user_id),
    service: XirrService = Depends(get_xirr_service),
):
    xirr, alpha = service.compute_xirr_and_alpha(user_id)
    return XirrResponse(
        xirr=xirr,
        xirr_percent=round(xirr * 100, 4) if xirr is not None else None,
        alpha=alpha,
        alpha_percent=round(alpha * 100, 4) if alpha is not None else None,
        beta=None,
        benchmark="Nifty 50",
    )
