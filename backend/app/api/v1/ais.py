from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.ais_line_repository import AisLineRepository
from app.repositories.ais_match_result_repository import AisMatchResultRepository
from app.repositories.ais_upload_repository import AisUploadRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.schemas.ais import (
    AisBulkResolveResponse,
    AisMatchResultResponse,
    AisMismatchListResponse,
    AisResolutionRequest,
    AisUploadDetailResponse,
    AisUploadHistoryResponse,
)
from app.services.ais_matching_service import AisMatchingService
from app.services.ais_parser_service import AisParserService
from app.services.ais_service import AisService

router = APIRouter()


def get_ais_service(db: Session = Depends(get_db)) -> AisService:
    return AisService(
        ais_upload_repository=AisUploadRepository(db),
        ais_line_repository=AisLineRepository(db),
        ais_match_result_repository=AisMatchResultRepository(db),
        ais_parser_service=AisParserService(),
        ais_matching_service=AisMatchingService(
            realized_gain_repository=RealizedGainRepository(db)
        ),
    )


@router.post("/ais/upload", response_model=AisUploadDetailResponse)
async def upload_ais(
    assessment_year: str,
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    service: AisService = Depends(get_ais_service),
):
    try:
        file_content = await file.read()
        result = service.upload(
            user_id=user_id,
            assessment_year=assessment_year,
            file_content=file_content,
            filename=file.filename,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get(
    "/ais/uploads/{assessment_year}/history",
    response_model=AisUploadHistoryResponse,
)
def get_upload_history(
    assessment_year: str,
    user_id: UUID = Depends(get_current_user_id),
    service: AisService = Depends(get_ais_service),
):
    return service.get_upload_history(user_id=user_id, assessment_year=assessment_year)


@router.get("/ais/uploads/{upload_id}", response_model=AisUploadDetailResponse)
def get_upload_detail(
    upload_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: AisService = Depends(get_ais_service),
):
    result = service.get_upload_detail(user_id=user_id, upload_id=upload_id)
    if not result:
        raise HTTPException(
            status_code=404, detail=f"AIS upload {upload_id} not found."
        )
    return result


@router.get(
    "/ais/uploads/{upload_id}/mismatches",
    response_model=AisMismatchListResponse,
)
def get_mismatches(
    upload_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: AisService = Depends(get_ais_service),
):
    lines = service.get_mismatches(user_id=user_id, upload_id=upload_id)
    if lines is None:
        raise HTTPException(
            status_code=404, detail=f"AIS upload {upload_id} not found."
        )
    return {"lines": lines}


@router.post(
    "/ais/uploads/{upload_id}/bulk-resolve-exact",
    response_model=AisBulkResolveResponse,
)
def bulk_resolve_exact(
    upload_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: AisService = Depends(get_ais_service),
):
    resolved_count = service.bulk_resolve_exact(user_id=user_id, upload_id=upload_id)
    if resolved_count is None:
        raise HTTPException(
            status_code=404, detail=f"AIS upload {upload_id} not found."
        )
    return {"resolved_count": resolved_count}


@router.patch(
    "/ais/match-results/{match_result_id}",
    response_model=AisMatchResultResponse,
)
def resolve_match_result(
    match_result_id: UUID,
    request: AisResolutionRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: AisService = Depends(get_ais_service),
):
    result = service.resolve_match_result(
        user_id=user_id,
        match_result_id=match_result_id,
        resolution_notes=request.resolution_notes,
    )
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"AIS match result {match_result_id} not found.",
        )
    return result


@router.delete("/ais/uploads/{upload_id}", status_code=204)
def delete_upload(
    upload_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: AisService = Depends(get_ais_service),
):
    deleted = service.delete_upload(user_id=user_id, upload_id=upload_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"AIS upload {upload_id} not found."
        )
