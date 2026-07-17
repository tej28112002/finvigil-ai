from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.config import settings
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
from app.services.upstox_service import UpstoxService

router = APIRouter()


class UpstoxLoginResponse(BaseModel):
    login_url: str


def get_upstox_service(
    db: Session = Depends(get_db)
) -> UpstoxService:
    return UpstoxService(
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
    "/brokers/upstox/login",
    response_model=UpstoxLoginResponse
)
def get_upstox_login_url(
    user_id: UUID = Depends(get_current_user_id),
    service: UpstoxService = Depends(get_upstox_service)
):
    try:
        login_url = service.get_login_url(user_id=user_id)
        return UpstoxLoginResponse(login_url=login_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/brokers/upstox/callback")
def upstox_callback(
    code: str,
    state: str,
    # Deliberately NOT auth-gated -- same reasoning as
    # /brokers/zerodha/callback (app/api/v1/zerodha.py): this is a raw
    # browser redirect from Upstox, which can't carry an Authorization
    # header. `state` is the same signed, short-lived token
    # (app/core/oauth_state.py) generated at GET /brokers/upstox/login time.
    service: UpstoxService = Depends(get_upstox_service)
):
    try:
        service.handle_callback(
            state=state,
            code=code,
        )
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/brokers?upstox=connected"
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/brokers?upstox=error&message={quote(str(e))}"
        )


@router.post(
    "/brokers/upstox/sync",
    response_model=CsvImportResponse
)
def sync_upstox_trades(
    broker_connection_id: UUID,
    service: UpstoxService = Depends(get_upstox_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        return service.sync_today_trades(
            user_id=user_id,
            broker_connection_id=broker_connection_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
