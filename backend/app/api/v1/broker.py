from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.broker_connection_repository import BrokerConnectionRepository
from app.services.broker_service import BrokerService
from app.schemas.broker import BrokerConnectRequest, BrokerConnectionResponse

router = APIRouter()


def get_broker_service(
    db: Session = Depends(get_db)
) -> BrokerService:
    repo = BrokerConnectionRepository(db)
    return BrokerService(broker_repository=repo)


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
        return service.connect_broker(
            user_id=user_id,
            broker_name=request.broker_name,
            credentials_kms_id=request.credentials_kms_id
        )
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
    return service.get_connections(user_id=user_id)


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
        return service.disconnect_broker(
            user_id=user_id,
            connection_id=connection_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
