from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.trade_repository import TradeRepository
from app.services.trading_analytics_service import TradingAnalyticsService

router = APIRouter()


def get_trading_analytics_service(
    db: Session = Depends(get_db),
) -> TradingAnalyticsService:
    return TradingAnalyticsService(
        realized_gain_repository=RealizedGainRepository(db),
        trade_repository=TradeRepository(db),
        holding_lot_repository=HoldingLotRepository(db),
        dashboard_repository=DashboardRepository(db),
    )


@router.get("/journal/analytics")
def get_journal_analytics(
    user_id: UUID = Depends(get_current_user_id),
    service: TradingAnalyticsService = Depends(get_trading_analytics_service),
):
    return service.compute_all(user_id)
