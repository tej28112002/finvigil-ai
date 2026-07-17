from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
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
from app.services.groww_service import GrowwService
from app.services.holding_service import HoldingLotService
from app.services.trade_service import TradeService

router = APIRouter()


def get_groww_service(
    db: Session = Depends(get_db)
) -> GrowwService:
    return GrowwService(
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


@router.post(
    "/brokers/groww/sync",
    response_model=CsvImportResponse
)
def sync_groww_trades(
    broker_connection_id: UUID,
    service: GrowwService = Depends(get_groww_service),
    user_id: UUID = Depends(get_current_user_id),
):
    # No login/callback endpoints here -- unlike Zerodha/Upstox, Groww has
    # no OAuth redirect. Credentials are submitted via the generic
    # POST /brokers/groww/credentials (app/api/v1/broker.py), and the
    # access token is generated fresh from the TOTP secret on every sync
    # (see GrowwService.refresh_access_token).
    try:
        return service.sync_today_trades(
            user_id=user_id,
            broker_connection_id=broker_connection_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
