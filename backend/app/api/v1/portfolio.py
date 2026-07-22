import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.portfolio import PortfolioItemResponse, XirrResponse
from app.services.nifty_service import NiftyService
from app.services.portfolio_service import PortfolioService
from app.services.xirr_service import XirrService

logger = logging.getLogger(__name__)

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
        realized_gain_repository=RealizedGainRepository(db),
    )


def get_nifty_service() -> NiftyService:
    return NiftyService()


def get_holding_lot_repository(db: Session = Depends(get_db)) -> HoldingLotRepository:
    return HoldingLotRepository(db)


def get_trade_repository(db: Session = Depends(get_db)) -> TradeRepository:
    return TradeRepository(db)


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
    nifty_service: NiftyService = Depends(get_nifty_service),
    holding_repo: HoldingLotRepository = Depends(get_holding_lot_repository),
    trade_repo: TradeRepository = Depends(get_trade_repository),
):
    # Fetched once here and passed into the Phase B (yfinance) metrics below
    # so each one doesn't re-query lots/trades from the DB independently.
    lots = holding_repo.get_active_lots_by_user(user_id)
    trades = trade_repo.get_by_user(user_id)

    # Every metric is wrapped in its own try/except: one computation failing
    # (e.g. a scipy/yfinance edge case) must never take down the rest of
    # this response.
    try:
        xirr, alpha = service.compute_xirr_and_alpha(user_id)
    except Exception as e:
        logger.warning(f"portfolio/xirr metric failed: {type(e).__name__}: {e}")
        xirr, alpha = None, None

    try:
        absolute_return = service.compute_absolute_return(user_id)
    except Exception as e:
        logger.warning(f"portfolio/xirr metric failed: {type(e).__name__}: {e}")
        absolute_return = None

    try:
        cagr = service.compute_cagr(user_id)
    except Exception as e:
        logger.warning(f"portfolio/xirr metric failed: {type(e).__name__}: {e}")
        cagr = None

    try:
        asset_allocation = service.compute_asset_allocation(user_id)
    except Exception as e:
        logger.warning(f"portfolio/xirr metric failed: {type(e).__name__}: {e}")
        asset_allocation = None

    try:
        top_holdings = service.compute_concentration(user_id)
    except Exception as e:
        logger.warning(f"portfolio/xirr metric failed: {type(e).__name__}: {e}")
        top_holdings = None

    try:
        current_value = service.get_current_value(user_id)
    except Exception as e:
        logger.warning(f"portfolio/xirr metric failed: {type(e).__name__}: {e}")
        current_value = None

    xirr_percent = round(xirr * 100, 4) if xirr is not None else None

    try:
        volatility = nifty_service.compute_volatility(user_id, lots, trades)
    except Exception as e:
        logger.warning(f"portfolio/xirr metric failed: {type(e).__name__}: {e}")
        volatility = None

    try:
        max_drawdown = nifty_service.compute_max_drawdown(user_id, lots, trades)
    except Exception as e:
        logger.warning(f"portfolio/xirr metric failed: {type(e).__name__}: {e}")
        max_drawdown = None

    try:
        beta = nifty_service.compute_beta(user_id, lots, trades)
    except Exception as e:
        logger.warning(f"portfolio/xirr metric failed: {type(e).__name__}: {e}")
        beta = None

    try:
        sharpe = nifty_service.compute_sharpe(user_id, lots, trades, xirr_percent)
    except Exception as e:
        logger.warning(f"portfolio/xirr metric failed: {type(e).__name__}: {e}")
        sharpe = None

    try:
        sortino = nifty_service.compute_sortino(user_id, lots, trades, xirr_percent)
    except Exception as e:
        logger.warning(f"portfolio/xirr metric failed: {type(e).__name__}: {e}")
        sortino = None

    try:
        var_95 = nifty_service.compute_var_95(user_id, lots, trades, current_value)
    except Exception as e:
        logger.warning(f"portfolio/xirr metric failed: {type(e).__name__}: {e}")
        var_95 = None

    return XirrResponse(
        xirr=xirr,
        xirr_percent=xirr_percent,
        alpha=alpha,
        alpha_percent=round(alpha * 100, 4) if alpha is not None else None,
        beta=beta,
        benchmark="Nifty 50",
        absolute_return_percent=absolute_return,
        cagr_percent=cagr,
        asset_allocation=asset_allocation,
        top_holdings=top_holdings,
        volatility_percent=volatility,
        max_drawdown_percent=max_drawdown,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        var_95_rupees=var_95,
    )
