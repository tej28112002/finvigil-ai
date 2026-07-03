from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.broker_connection_repository import BrokerConnectionRepository
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.vault_repository import VaultRepository
from app.schemas.dashboard import DashboardProjectionResponse
from app.services.dashboard_service import DashboardService
from app.services.price_service import PriceService

router = APIRouter()


def get_dashboard_service(
    db: Session = Depends(get_db)
) -> DashboardService:
    dashboard_repo = DashboardRepository(db)
    holding_repo = HoldingLotRepository(db)
    broker_repo = BrokerConnectionRepository(db)
    vault_repo = VaultRepository(db)
    price_svc = PriceService(
        broker_connection_repository=broker_repo,
        vault_repository=vault_repo,
    )
    return DashboardService(
        dashboard_repository=dashboard_repo,
        holding_repository=holding_repo,
        price_service=price_svc,
    )


@router.get(
    "/dashboard/",
    response_model=DashboardProjectionResponse
)
def get_dashboard(
    user_id: UUID = Depends(get_current_user_id),
    service: DashboardService = Depends(get_dashboard_service)
):
    return service.calculate_and_update_projection(
        user_id=user_id
    )


@router.get(
    "/dashboard/cached",
    response_model=DashboardProjectionResponse
)
def get_cached_dashboard(
    user_id: UUID = Depends(get_current_user_id),
    service: DashboardService = Depends(get_dashboard_service)
):
    projection = service.get_projection(user_id=user_id)
    if not projection:
        raise HTTPException(
            status_code=404,
            detail=f"No dashboard projection found for user {user_id}. "
                   f"Call GET /dashboard/ first to generate one."
        )
    return projection
