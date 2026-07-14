import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.trade import TradeIngestRequest, TradeResponse
from app.services.holding_service import HoldingLotService
from app.services.instrument_service import InstrumentService
from app.services.trade_service import TradeService

router = APIRouter()


def get_trade_service(
    db: Session = Depends(get_db)
) -> TradeService:
    trade_repo = TradeRepository(db)
    holding_repo = HoldingLotRepository(db)
    holding_svc = HoldingLotService(
        holding_repository=holding_repo
    )
    realized_gain_repo = RealizedGainRepository(db)
    return TradeService(
        trade_repository=trade_repo,
        holding_service=holding_svc,
        realized_gain_repository=realized_gain_repo
    )


def get_instrument_service(
    db: Session = Depends(get_db)
) -> InstrumentService:
    instrument_repo = InstrumentRepository(db)
    return InstrumentService(
        instrument_repository=instrument_repo
    )


@router.post(
    "/trades/ingest",
    response_model=TradeResponse
)
def ingest_trade(
    request: TradeIngestRequest,
    user_id: UUID = Depends(get_current_user_id),
    trade_service: TradeService = Depends(get_trade_service),
    instrument_service: InstrumentService = Depends(get_instrument_service)
):
    try:
        instrument = instrument_service.get_or_create_instrument(
            symbol=request.symbol,
            instrument_type=request.instrument_type,
            name=request.instrument_name,
            isin=request.isin
        )

        raw = f"{request.broker_connection_id}:{request.broker_trade_id}"
        idempotency_hash = hashlib.sha256(raw.encode()).hexdigest()

        return trade_service.process_trade(
            trade_type=request.trade_type,
            user_id=user_id,
            instrument_id=instrument.id,
            broker_connection_id=request.broker_connection_id,
            broker_trade_id=request.broker_trade_id,
            quantity=request.quantity,
            price=request.price,
            execution_time=request.execution_time,
            idempotency_hash=idempotency_hash
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/trades/",
    response_model=list[TradeResponse]
)
def list_trades(
    user_id: UUID = Depends(get_current_user_id),
    trade_service: TradeService = Depends(get_trade_service)
):
    return trade_service.get_trades_by_user(user_id=user_id)


@router.get(
    "/trades/{trade_id}",
    response_model=TradeResponse
)
def get_trade(
    trade_id: UUID,
    trade_service: TradeService = Depends(get_trade_service),
    user_id: UUID = Depends(get_current_user_id),
):
    # Ownership enforced in the query (trade_id AND user_id) — another
    # user's trade produces the same None as a nonexistent trade_id, so
    # this 404 never confirms whether the UUID belongs to anyone.
    trade = trade_service.get_trade_by_id(trade_id=trade_id, user_id=user_id)
    if not trade:
        raise HTTPException(
            status_code=404,
            detail=f"Trade {trade_id} not found."
        )
    return trade
