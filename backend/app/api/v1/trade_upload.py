from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.broker_connection_repository import BrokerConnectionRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.trade_repository import TradeRepository
from app.services.holding_service import HoldingLotService
from app.services.instrument_service import InstrumentService
from app.services.trade_service import TradeService
from app.services.trade_upload_service import MAX_UPLOAD_BYTES, TradeUploadService

router = APIRouter()


def get_trade_upload_service(db: Session = Depends(get_db)) -> TradeUploadService:
    trade_repo = TradeRepository(db)
    trade_service = TradeService(
        trade_repository=trade_repo,
        holding_service=HoldingLotService(holding_repository=HoldingLotRepository(db)),
        realized_gain_repository=RealizedGainRepository(db),
    )
    return TradeUploadService(
        trade_repository=trade_repo,
        instrument_service=InstrumentService(instrument_repository=InstrumentRepository(db)),
        broker_connection_repository=BrokerConnectionRepository(db),
        trade_service=trade_service,
    )


@router.post("/trades/upload-csv")
async def upload_trades_csv(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    service: TradeUploadService = Depends(get_trade_upload_service),
):
    file_content = await file.read()
    if len(file_content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")

    return service.process_upload(
        file_content=file_content,
        filename=file.filename or "",
        user_id=user_id,
    )
