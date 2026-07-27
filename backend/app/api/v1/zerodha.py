from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.dashboard import get_dashboard_service
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
from app.schemas.broker import BrokerSyncResponse
from app.services.dashboard_service import DashboardService
from app.services.holding_service import HoldingLotService
from app.services.trade_service import TradeService
from app.services.zerodha_service import ZerodhaService

router = APIRouter()


class ZerodhaLoginResponse(BaseModel):
    login_url: str


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
        holding_lot_repository=HoldingLotRepository(db),
    )


@router.get(
    "/brokers/zerodha/login",
    response_model=ZerodhaLoginResponse
)
def get_zerodha_login_url(
    user_id: UUID = Depends(get_current_user_id),
    service: ZerodhaService = Depends(get_zerodha_service)
):
    try:
        login_url = service.get_login_url(user_id=user_id)
        return ZerodhaLoginResponse(login_url=login_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/brokers/zerodha/callback")
def zerodha_callback(
    request_token: str,
    state: str,
    # Deliberately NOT auth-gated: this endpoint is hit by a raw browser
    # redirect FROM Zerodha, which cannot carry an Authorization header.
    # `state` is a signed, short-lived token (app/core/oauth_state.py)
    # generated at GET /brokers/zerodha/login time and carried through via
    # Kite Connect's redirect_params mechanism -- replaces the previous bare
    # user_id query param (documented tech debt, now closed).
    #
    # Redirects the browser straight back into the app instead of returning
    # JSON -- now that `state` carries the user identity securely, the old
    # "copy the request_token out of the failed redirect and paste it into
    # this URL yourself" manual step (Phase 4.5's known follow-up) is no
    # longer needed.
    service: ZerodhaService = Depends(get_zerodha_service)
):
    try:
        service.handle_callback(
            state=state,
            request_token=request_token,
        )
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/brokers?zerodha=connected"
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/brokers?zerodha=error&message={quote(str(e))}"
        )


@router.post(
    "/brokers/zerodha/sync",
    response_model=BrokerSyncResponse
)
def sync_zerodha_trades(
    broker_connection_id: UUID,
    service: ZerodhaService = Depends(get_zerodha_service),
    user_id: UUID = Depends(get_current_user_id),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
):
    # sync_broker() never raises -- credential/token/network failures come
    # back as {success: False, error_code: ...} so the frontend can show a
    # specific, actionable message instead of a generic error banner.
    result = service.sync_broker(
        user_id=user_id,
        broker_connection_id=broker_connection_id,
    )
    if result.get("success"):
        try:
            dashboard_service.calculate_and_update_projection(user_id=user_id)
        except Exception:
            pass
    return BrokerSyncResponse(**result)
