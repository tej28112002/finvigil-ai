import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.tds_ledger_repository import TdsLedgerRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.crypto import (
    CryptoTaxSummaryResponse,
    CryptoTradeIngestRequest,
    CryptoTradeResponse,
)
from app.services.crypto_service import CryptoService
from app.services.crypto_tax_service import CryptoTaxService
from app.services.holding_service import HoldingLotService

router = APIRouter()


def get_crypto_service(db: Session = Depends(get_db)) -> CryptoService:
    instrument_repo = InstrumentRepository(db)
    trade_repo = TradeRepository(db)
    holding_repo = HoldingLotRepository(db)
    holding_svc = HoldingLotService(holding_repository=holding_repo)
    realized_gain_repo = RealizedGainRepository(db)
    tds_repo = TdsLedgerRepository(db)
    return CryptoService(
        instrument_repository=instrument_repo,
        trade_repository=trade_repo,
        holding_service=holding_svc,
        realized_gain_repository=realized_gain_repo,
        tds_ledger_repository=tds_repo,
    )


def get_crypto_tax_service(db: Session = Depends(get_db)) -> CryptoTaxService:
    realized_gain_repo = RealizedGainRepository(db)
    tds_repo = TdsLedgerRepository(db)
    return CryptoTaxService(
        realized_gain_repository=realized_gain_repo,
        tds_ledger_repository=tds_repo,
    )


@router.post(
    "/crypto/ingest",
    response_model=CryptoTradeResponse
)
def ingest_crypto_trade(
    request: CryptoTradeIngestRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: CryptoService = Depends(get_crypto_service)
):
    try:
        raw = f"{request.broker_connection_id}:{request.broker_trade_id}"
        idempotency_hash = hashlib.sha256(raw.encode()).hexdigest()

        return service.ingest_crypto_trade(
            user_id=user_id,
            broker_connection_id=request.broker_connection_id,
            broker_trade_id=request.broker_trade_id,
            trade_type=request.trade_type,
            symbol=request.symbol,
            instrument_name=request.instrument_name,
            quantity=request.quantity,
            price=request.price,
            execution_time=request.execution_time,
            idempotency_hash=idempotency_hash,
            isin=request.isin,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/crypto/tax/{assessment_year}",
    response_model=CryptoTaxSummaryResponse
)
def get_crypto_tax(
    assessment_year: str,
    user_id: UUID = Depends(get_current_user_id),
    service: CryptoTaxService = Depends(get_crypto_tax_service)
):
    result = service.calculate_crypto_tax(
        user_id=user_id,
        assessment_year=assessment_year,
    )
    return CryptoTaxSummaryResponse(**result)
