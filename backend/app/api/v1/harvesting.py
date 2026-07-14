from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.broker_connection_repository import BrokerConnectionRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.vault_repository import VaultRepository
from app.schemas.harvesting import HarvestCandidateResponse, HarvestSummaryResponse
from app.services.harvesting_service import HarvestingService
from app.services.price_service import PriceService

router = APIRouter()


def get_harvesting_service(
    db: Session = Depends(get_db)
) -> HarvestingService:
    holding_repo = HoldingLotRepository(db)
    realized_gain_repo = RealizedGainRepository(db)
    broker_repo = BrokerConnectionRepository(db)
    vault_repo = VaultRepository(db)
    price_svc = PriceService(
        broker_connection_repository=broker_repo,
        vault_repository=vault_repo,
    )
    return HarvestingService(
        holding_repository=holding_repo,
        realized_gain_repository=realized_gain_repo,
        price_service=price_svc,
    )


@router.get(
    "/harvesting/candidates/{assessment_year}",
    response_model=list[HarvestCandidateResponse]
)
def get_harvest_candidates(
    assessment_year: str,
    user_id: UUID = Depends(get_current_user_id),
    service: HarvestingService = Depends(get_harvesting_service)
):
    return service.get_harvest_candidates(
        user_id=user_id,
        assessment_year=assessment_year,
    )


@router.get(
    "/harvesting/summary/{assessment_year}",
    response_model=HarvestSummaryResponse
)
def get_harvest_summary(
    assessment_year: str,
    user_id: UUID = Depends(get_current_user_id),
    service: HarvestingService = Depends(get_harvesting_service)
):
    return service.get_harvest_summary(
        user_id=user_id,
        assessment_year=assessment_year,
    )
