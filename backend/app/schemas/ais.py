from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

_AIS_DISCLAIMER = (
    "AIS reconciliation compares your AIS-reported figures against "
    "FinVigil's own computed totals at the section/category level, not "
    "transaction-by-transaction — the AIS/TIS portal itself reports "
    "aggregated figures per source. Category detection uses a keyword "
    "heuristic, not official CBDT/SFT code tables. Always verify against "
    "the original AIS/TIS PDF and consult your CA before filing."
)


class AisUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_year: str
    version: int
    is_latest: bool
    upload_date: datetime
    created_at: datetime


class AisLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    section_code: str
    description: str | None
    reported_amount: Decimal | None


class AisMatchResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ais_line_id: UUID
    match_status: str
    mismatch_type: str | None
    resolution_notes: str | None


class AisLineWithMatchResponse(BaseModel):
    line: AisLineResponse
    match_result: AisMatchResultResponse | None


class AisUploadSummary(BaseModel):
    upload: AisUploadResponse
    total_lines: int
    matched_count: int
    mismatch_count: int
    unresolved_count: int
    match_percentage: Decimal


class AisUploadDetailResponse(BaseModel):
    summary: AisUploadSummary
    lines: list[AisLineWithMatchResponse]
    disclaimer: str = _AIS_DISCLAIMER


class AisUploadHistoryResponse(BaseModel):
    assessment_year: str
    versions: list[AisUploadSummary]


class AisMismatchListResponse(BaseModel):
    lines: list[AisLineWithMatchResponse]
    disclaimer: str = _AIS_DISCLAIMER


class AisResolutionRequest(BaseModel):
    resolution_notes: str


class AisBulkResolveResponse(BaseModel):
    resolved_count: int
