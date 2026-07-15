from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.tax_summary_repository import TaxSummaryRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.ca_export_job_repository import CaExportJobRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.itr_schema_repository import ItrSchemaRepository
from app.services.tax_export_service import TaxExportService
from app.services.itr3_export_service import ITR3ExportService, ItrSchemaNotFoundError
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


def get_itr3_export_service(
    db: Session = Depends(get_db)
) -> ITR3ExportService:
    return ITR3ExportService(
        itr_schema_repository=ItrSchemaRepository(db),
        realized_gain_repository=RealizedGainRepository(db),
        tax_summary_repository=TaxSummaryRepository(db),
        instrument_repository=InstrumentRepository(db),
    )


@router.post(
    "/tax/export",
    response_model=CapitalGainsExportResponse
)
def export_capital_gains(
    request: TaxExportRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: TaxExportService = Depends(get_tax_export_service)
):
    try:
        return service.generate_export(
            user_id=user_id,
            assessment_year=request.assessment_year
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tax/itr3-export")
def export_itr3(
    request: TaxExportRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: ITR3ExportService = Depends(get_itr3_export_service),
):
    try:
        result = service.generate_export(
            user_id=user_id,
            assessment_year=request.assessment_year,
        )
    except ItrSchemaNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    ay = request.assessment_year
    return JSONResponse(
        content=result,
        headers={
            "Content-Disposition": f"attachment; filename=itr3_{ay}.json",
        },
    )
