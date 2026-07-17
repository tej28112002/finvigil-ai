from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.broker_connection_repository import BrokerConnectionRepository
from app.repositories.vault_repository import VaultRepository
from app.services.broker_service import BrokerService
from app.schemas.broker import (
    BrokerConnectRequest,
    BrokerConnectionResponse,
    BrokerCredentialsRequest,
)

router = APIRouter()


def get_broker_service(
    db: Session = Depends(get_db)
) -> BrokerService:
    repo = BrokerConnectionRepository(db)
    return BrokerService(
        broker_repository=repo,
        vault_repository=VaultRepository(db),
    )


@router.post(
    "/brokers/connect",
    response_model=BrokerConnectionResponse
)
def connect_broker(
    request: BrokerConnectRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: BrokerService = Depends(get_broker_service)
):
    try:
        connection = service.connect_broker(
            user_id=user_id,
            broker_name=request.broker_name,
        )
        return BrokerConnectionResponse.from_connection(connection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/brokers/{broker_name}/credentials",
    response_model=BrokerConnectionResponse
)
def submit_broker_credentials(
    broker_name: str,
    request: BrokerCredentialsRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: BrokerService = Depends(get_broker_service)
):
    try:
        connection = service.submit_credentials(
            user_id=user_id,
            broker_name=broker_name,
            api_key=request.api_key,
            api_secret=request.api_secret,
            totp_secret=request.totp_secret,
        )
        return BrokerConnectionResponse.from_connection(connection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/brokers/",
    response_model=list[BrokerConnectionResponse]
)
def list_brokers(
    user_id: UUID = Depends(get_current_user_id),
    service: BrokerService = Depends(get_broker_service)
):
    connections = service.get_connections(user_id=user_id)
    return [BrokerConnectionResponse.from_connection(c) for c in connections]


@router.delete(
    "/brokers/{connection_id}",
    response_model=BrokerConnectionResponse
)
def disconnect_broker(
    connection_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: BrokerService = Depends(get_broker_service)
):
    try:
        connection = service.disconnect_broker(
            user_id=user_id,
            connection_id=connection_id
        )
        return BrokerConnectionResponse.from_connection(connection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
