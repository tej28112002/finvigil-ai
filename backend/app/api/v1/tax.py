from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.tax_summary_repository import TaxSummaryRepository
from app.schemas.tax_summary import TaxCalculationRequest, TaxSummaryResponse
from app.services.tax_engine_service import TaxEngineService

router = APIRouter()


def get_tax_engine_service(
    db: Session = Depends(get_db)
) -> TaxEngineService:
    tax_summary_repo = TaxSummaryRepository(db)
    realized_gain_repo = RealizedGainRepository(db)
    return TaxEngineService(
        tax_summary_repository=tax_summary_repo,
        realized_gain_repository=realized_gain_repo
    )


@router.post(
    "/tax/calculate",
    response_model=TaxSummaryResponse
)
def calculate_tax(
    request: TaxCalculationRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: TaxEngineService = Depends(get_tax_engine_service)
):
    return service.calculate_tax_summary(
        user_id=user_id,
        assessment_year=request.assessment_year
    )


@router.get(
    "/tax/summary/",
    response_model=list[TaxSummaryResponse]
)
def list_tax_summaries(
    user_id: UUID = Depends(get_current_user_id),
    service: TaxEngineService = Depends(get_tax_engine_service)
):
    return service.get_all_tax_summaries(user_id=user_id)


@router.get(
    "/tax/summary/{assessment_year}",
    response_model=TaxSummaryResponse
)
def get_tax_summary(
    assessment_year: str,
    user_id: UUID = Depends(get_current_user_id),
    service: TaxEngineService = Depends(get_tax_engine_service)
):
    summary = service.get_tax_summary(
        user_id=user_id,
        assessment_year=assessment_year
    )
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=f"No tax summary found for assessment year {assessment_year}. "
                   f"Call POST /tax/calculate first to generate one."
        )
    return summary
