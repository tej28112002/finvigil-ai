from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.trade_repository import TradeRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.services.csv_parser_service import CsvParserService
from app.services.trade_service import TradeService
from app.services.holding_service import HoldingLotService
from app.services.csv_import_service import CsvImportService
from app.schemas.csv_import import CsvImportResponse

router = APIRouter()


def get_csv_import_service(
    db: Session = Depends(get_db)
) -> CsvImportService:
    csv_parser_service = CsvParserService()
    trade_service = TradeService(
        trade_repository=TradeRepository(db),
        holding_service=HoldingLotService(
            holding_repository=HoldingLotRepository(db)
        ),
        realized_gain_repository=RealizedGainRepository(db),
    )
    instrument_repository = InstrumentRepository(db)
    return CsvImportService(
        csv_parser_service=csv_parser_service,
        trade_service=trade_service,
        instrument_repository=instrument_repository,
    )


@router.post(
    "/csv-import/tradebook",
    response_model=CsvImportResponse
)
async def import_tradebook(
    broker_connection_id: UUID,
    file: UploadFile = File(...),
    service: CsvImportService = Depends(get_csv_import_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        file_content = await file.read()
        return service.import_tradebook(
            file_content=file_content,
            filename=file.filename,
            user_id=user_id,
            broker_connection_id=broker_connection_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
