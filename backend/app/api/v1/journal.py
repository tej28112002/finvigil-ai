from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.journal_taxonomy import PSYCHOLOGY_TAGS
from app.db.session import get_db
from app.repositories.journal_entry_repository import JournalEntryRepository
from app.repositories.journal_tag_repository import JournalTagRepository
from app.schemas.journal import (
    JournalAddTagsRequest,
    JournalEntryWithTagsResponse,
    JournalTagResponse,
    JournalTaxonomyResponse,
    JournalTextEntryRequest,
)
from app.services.journal_service import JournalService

router = APIRouter()


def get_journal_service(db: Session = Depends(get_db)) -> JournalService:
    return JournalService(
        journal_entry_repository=JournalEntryRepository(db),
        journal_tag_repository=JournalTagRepository(db),
    )


@router.get("/journal/tags/taxonomy", response_model=JournalTaxonomyResponse)
def get_taxonomy():
    return JournalTaxonomyResponse(tags=PSYCHOLOGY_TAGS)


@router.post("/journal/entries/audio", response_model=JournalEntryWithTagsResponse)
async def create_entry_from_audio(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    service: JournalService = Depends(get_journal_service),
):
    audio_bytes = await file.read()
    try:
        entry = service.create_entry_from_audio(
            user_id=user_id, audio_bytes=audio_bytes, filename=file.filename or "recording.webm"
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {e}")

    return {"entry": entry, "tags": []}


@router.post("/journal/entries/text", response_model=JournalEntryWithTagsResponse)
def create_entry_from_text(
    request: JournalTextEntryRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: JournalService = Depends(get_journal_service),
):
    try:
        entry = service.create_entry_from_text(
            user_id=user_id, transcript=request.transcript
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"entry": entry, "tags": []}


@router.get("/journal/entries", response_model=list[JournalEntryWithTagsResponse])
def list_entries(
    user_id: UUID = Depends(get_current_user_id),
    service: JournalService = Depends(get_journal_service),
):
    return service.get_entries(user_id)


@router.get("/journal/entries/{entry_id}", response_model=JournalEntryWithTagsResponse)
def get_entry(
    entry_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: JournalService = Depends(get_journal_service),
):
    result = service.get_entry_detail(user_id=user_id, entry_id=entry_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Journal entry {entry_id} not found.")
    return result


@router.post("/journal/entries/{entry_id}/tags", response_model=list[JournalTagResponse])
def add_tags(
    entry_id: UUID,
    request: JournalAddTagsRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: JournalService = Depends(get_journal_service),
):
    try:
        tags = service.add_tags(
            user_id=user_id, entry_id=entry_id, tag_names=request.tag_names
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if tags is None:
        raise HTTPException(status_code=404, detail=f"Journal entry {entry_id} not found.")
    return tags


@router.delete("/journal/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: JournalService = Depends(get_journal_service),
):
    deleted = service.delete_entry(user_id=user_id, entry_id=entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Journal entry {entry_id} not found.")
