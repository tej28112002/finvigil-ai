from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.tax_summary_repository import TaxSummaryRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.ca_export_job_repository import CaExportJobRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.services.tax_export_service import TaxExportService
from app.schemas.tax_export import TaxExportRequest, CapitalGainsExportResponse

router = APIRouter()


def get_tax_export_service(
    db: Session = Depends(get_db)
) -> TaxExportService:
    return TaxExportService(
        tax_summary_repository=TaxSummaryRepository(db),
        realized_gain_repository=RealizedGainRepository(db),
        ca_export_job_repository=CaExportJobRepository(db),
        instrument_repository=InstrumentRepository(db),
    )


@router.post(
    "/tax/export",
    response_model=CapitalGainsExportResponse
)
def export_capital_gains(
    request: TaxExportRequest,
    user_id: UUID,
    service: TaxExportService = Depends(get_tax_export_service)
):
    try:
        return service.generate_export(
            user_id=user_id,
            assessment_year=request.assessment_year
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
