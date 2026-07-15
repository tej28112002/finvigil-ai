from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ItrSchemaMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ay: str
    schema_version: str
    is_active: bool
    uploaded_at: datetime


class ItrSchemaMappingDetailResponse(ItrSchemaMappingResponse):
    mapping_json: dict[str, Any]


class ItrSchemaUploadRequest(BaseModel):
    ay: str
    schema_version: str
    mapping_json: dict[str, Any]


class ItrSchemaActivateRequest(BaseModel):
    is_active: bool
