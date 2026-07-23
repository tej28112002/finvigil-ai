from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.services.tax_harvest_intelligence_service import TaxHarvestingIntelligenceService

router = APIRouter()


def get_tax_harvest_intelligence_service(
    db: Session = Depends(get_db),
) -> TaxHarvestingIntelligenceService:
    return TaxHarvestingIntelligenceService(
        realized_gain_repository=RealizedGainRepository(db),
        holding_lot_repository=HoldingLotRepository(db),
        dashboard_repository=DashboardRepository(db),
    )


@router.get("/tax-harvest/intelligence")
def get_tax_harvest_intelligence(
    user_id: UUID = Depends(get_current_user_id),
    service: TaxHarvestingIntelligenceService = Depends(get_tax_harvest_intelligence_service),
):
    return service.compute_all_strategies(user_id)
