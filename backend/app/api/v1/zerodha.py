from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.broker_connection_repository import (
    BrokerConnectionRepository,
)
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.trade_repository import TradeRepository
from app.repositories.vault_repository import VaultRepository
from app.schemas.csv_import import CsvImportResponse
from app.services.holding_service import HoldingLotService
from app.services.trade_service import TradeService
from app.services.zerodha_service import ZerodhaService

router = APIRouter()


class ZerodhaLoginResponse(BaseModel):
    login_url: str


class ZerodhaCallbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    broker_name: str
    status: str
    connected: bool = True


def get_zerodha_service(
    db: Session = Depends(get_db)
) -> ZerodhaService:
    return ZerodhaService(
        broker_connection_repository=BrokerConnectionRepository(db),
        vault_repository=VaultRepository(db),
        trade_service=TradeService(
            trade_repository=TradeRepository(db),
            holding_service=HoldingLotService(
                holding_repository=HoldingLotRepository(db)
            ),
            realized_gain_repository=RealizedGainRepository(db),
        ),
        instrument_repository=InstrumentRepository(db),
    )


@router.get(
    "/brokers/zerodha/login",
    response_model=ZerodhaLoginResponse
)
def get_zerodha_login_url(
    user_id: UUID,
    service: ZerodhaService = Depends(get_zerodha_service)
):
    try:
        login_url = service.get_login_url(user_id=user_id)
        return ZerodhaLoginResponse(login_url=login_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/brokers/zerodha/callback",
    response_model=ZerodhaCallbackResponse
)
def zerodha_callback(
    request_token: str,
    user_id: UUID,
    service: ZerodhaService = Depends(get_zerodha_service)
):
    try:
        connection = service.handle_callback(
            user_id=user_id,
            request_token=request_token,
        )
        return ZerodhaCallbackResponse(
            id=connection.id,
            user_id=connection.user_id,
            broker_name=connection.broker_name,
            status=connection.status,
            connected=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/brokers/zerodha/sync",
    response_model=CsvImportResponse
)
def sync_zerodha_trades(
    user_id: UUID,
    broker_connection_id: UUID,
    service: ZerodhaService = Depends(get_zerodha_service)
):
    try:
        return service.sync_today_trades(
            user_id=user_id,
            broker_connection_id=broker_connection_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
