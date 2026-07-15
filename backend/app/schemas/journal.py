from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JournalTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tag_name: str


class JournalEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transcript: str
    created_at: datetime


class JournalEntryWithTagsResponse(BaseModel):
    entry: JournalEntryResponse
    tags: list[JournalTagResponse]


class JournalTextEntryRequest(BaseModel):
    transcript: str


class JournalAddTagsRequest(BaseModel):
    tag_names: list[str]


class JournalTaxonomyResponse(BaseModel):
    tags: dict[str, str]
