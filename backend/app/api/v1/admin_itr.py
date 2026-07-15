from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.itr_schema_repository import ItrSchemaRepository
from app.schemas.itr_schema import (
    ItrSchemaActivateRequest,
    ItrSchemaMappingDetailResponse,
    ItrSchemaMappingResponse,
    ItrSchemaUploadRequest,
)

# NOTE: these endpoints only require authentication (get_current_user_id),
# not an admin role — a real admin-role check is planned for Phase 14
# (Admin Panel) and must be added before this is exposed beyond trusted
# operators. Until then, any authenticated user can upload/activate ITR
# schema mappings.
router = APIRouter()


def get_itr_schema_repository(db: Session = Depends(get_db)) -> ItrSchemaRepository:
    return ItrSchemaRepository(db)


@router.get("/admin/itr-schemas", response_model=list[ItrSchemaMappingResponse])
def list_itr_schemas(
    user_id: UUID = Depends(get_current_user_id),
    repo: ItrSchemaRepository = Depends(get_itr_schema_repository),
):
    return repo.get_all()


@router.post("/admin/itr-schemas", response_model=ItrSchemaMappingDetailResponse)
def upload_itr_schema(
    request: ItrSchemaUploadRequest,
    user_id: UUID = Depends(get_current_user_id),
    repo: ItrSchemaRepository = Depends(get_itr_schema_repository),
):
    return repo.create_or_update(
        ay=request.ay,
        schema_version=request.schema_version,
        mapping_json=request.mapping_json,
    )


@router.get(
    "/admin/itr-schemas/{ay}", response_model=ItrSchemaMappingDetailResponse
)
def get_itr_schema(
    ay: str,
    user_id: UUID = Depends(get_current_user_id),
    repo: ItrSchemaRepository = Depends(get_itr_schema_repository),
):
    mapping = repo.get_by_ay(ay)
    if not mapping:
        raise HTTPException(
            status_code=404, detail=f"No ITR schema mapping found for AY {ay}."
        )
    return mapping


@router.patch(
    "/admin/itr-schemas/{ay}", response_model=ItrSchemaMappingResponse
)
def set_itr_schema_active(
    ay: str,
    request: ItrSchemaActivateRequest,
    user_id: UUID = Depends(get_current_user_id),
    repo: ItrSchemaRepository = Depends(get_itr_schema_repository),
):
    mapping = repo.set_active(ay=ay, is_active=request.is_active)
    if not mapping:
        raise HTTPException(
            status_code=404, detail=f"No ITR schema mapping found for AY {ay}."
        )
    return mapping
