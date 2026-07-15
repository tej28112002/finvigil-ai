from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.admin_auth import get_current_admin_user_id
from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.itr_schema_repository import ItrSchemaRepository
from app.schemas.itr_schema import (
    ItrSchemaActivateRequest,
    ItrSchemaMappingDetailResponse,
    ItrSchemaMappingResponse,
    ItrSchemaUploadRequest,
)

# The two write endpoints (upload, activate/deactivate) require
# is_admin = TRUE on user_tax_personas via get_current_admin_user_id — a
# minimal role check, not the full RBAC model planned for Phase 14. Read
# endpoints (GET) stay on plain get_current_user_id: read-only, lower risk,
# and the frontend's ITR-3 download button on /tax needs GET
# /admin/itr-schemas to know which AYs are available for every user, not
# just admins.
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
    user_id: UUID = Depends(get_current_admin_user_id),
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
    user_id: UUID = Depends(get_current_admin_user_id),
    repo: ItrSchemaRepository = Depends(get_itr_schema_repository),
):
    mapping = repo.set_active(ay=ay, is_active=request.is_active)
    if not mapping:
        raise HTTPException(
            status_code=404, detail=f"No ITR schema mapping found for AY {ay}."
        )
    return mapping
