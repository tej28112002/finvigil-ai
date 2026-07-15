from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.broker_connection_repository import BrokerConnectionRepository
from app.repositories.tax_summary_repository import TaxSummaryRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.ca_export_job_repository import CaExportJobRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.itr_schema_repository import ItrSchemaRepository
from app.repositories.vault_repository import VaultRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.services.tax_export_service import TaxExportService
from app.services.itr3_export_service import ITR3ExportService, ItrSchemaNotFoundError
from app.services.ca_bundle_service import CABundleService
from app.services.harvesting_service import HarvestingService
from app.services.price_service import PriceService
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


def get_ca_bundle_service(
    db: Session = Depends(get_db)
) -> CABundleService:
    price_service = PriceService(
        broker_connection_repository=BrokerConnectionRepository(db),
        vault_repository=VaultRepository(db),
    )
    return CABundleService(
        itr3_export_service=ITR3ExportService(
            itr_schema_repository=ItrSchemaRepository(db),
            realized_gain_repository=RealizedGainRepository(db),
            tax_summary_repository=TaxSummaryRepository(db),
            instrument_repository=InstrumentRepository(db),
        ),
        tax_export_service=TaxExportService(
            tax_summary_repository=TaxSummaryRepository(db),
            realized_gain_repository=RealizedGainRepository(db),
            ca_export_job_repository=CaExportJobRepository(db),
            instrument_repository=InstrumentRepository(db),
        ),
        realized_gain_repository=RealizedGainRepository(db),
        instrument_repository=InstrumentRepository(db),
        harvesting_service=HarvestingService(
            holding_repository=HoldingLotRepository(db),
            realized_gain_repository=RealizedGainRepository(db),
            price_service=price_service,
        ),
        ca_export_job_repository=CaExportJobRepository(db),
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


@router.post("/tax/ca-bundle")
def export_ca_bundle(
    request: TaxExportRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: CABundleService = Depends(get_ca_bundle_service),
):
    ay = request.assessment_year
    try:
        zip_bytes = service.generate_bundle(user_id=user_id, assessment_year=ay)
    except ItrSchemaNotFoundError:
        raise HTTPException(
            status_code=400, detail=f"ITR-3 schema not available for {ay}"
        )
    except ValueError:
        raise HTTPException(
            status_code=404, detail="Run POST /tax/calculate first"
        )

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=finvigil_ca_bundle_{ay}.zip",
        },
    )
