from uuid import UUID

from app.core import groq_client
from app.core.journal_taxonomy import PSYCHOLOGY_TAGS
from app.models.journal_entry import JournalEntry
from app.repositories.journal_entry_repository import JournalEntryRepository
from app.repositories.journal_tag_repository import JournalTagRepository


class JournalService:
    """
    BRD FR-JRN-*: voice journal pipeline (transcribe -> store transcript
    only, never audio), fixed psychology taxonomy tagging, and
    delete-cascades-transcript-and-tags.
    """

    def __init__(
        self,
        journal_entry_repository: JournalEntryRepository,
        journal_tag_repository: JournalTagRepository,
    ):
        self.journal_entry_repository = journal_entry_repository
        self.journal_tag_repository = journal_tag_repository

    def create_entry_from_audio(
        self, user_id: UUID, audio_bytes: bytes, filename: str
    ) -> JournalEntry:
        """
        audio_bytes lives only in this call's stack frame — passed
        straight to groq_client.transcribe() and never written to disk or
        a DB column. Once this method returns, nothing in the process
        still references the raw audio; there is no separate "delete"
        step because it was never persisted.
        """
        transcript = groq_client.transcribe(audio_bytes, filename)
        return self.journal_entry_repository.create_entry(
            user_id=user_id, transcript=transcript
        )

    def create_entry_from_text(self, user_id: UUID, transcript: str) -> JournalEntry:
        """Text-entry fallback — for users without mic access, or typing
        instead of recording. No audio pipeline involved at all."""
        if not transcript.strip():
            raise ValueError("Journal entry text cannot be empty.")
        return self.journal_entry_repository.create_entry(
            user_id=user_id, transcript=transcript.strip()
        )

    def add_tags(
        self, user_id: UUID, entry_id: UUID, tag_names: list[str]
    ) -> list:
        entry = self.journal_entry_repository.get_by_id_and_user(entry_id, user_id)
        if not entry:
            return None

        invalid = [t for t in tag_names if t not in PSYCHOLOGY_TAGS]
        if invalid:
            raise ValueError(
                f"Invalid tag(s): {invalid}. Must be one of: {sorted(PSYCHOLOGY_TAGS)}"
            )

        # De-dupe against tags already on this entry — journal_tags has a
        # UNIQUE(journal_entry_id, tag_name) constraint at the DB level.
        existing = {t.tag_name for t in self.journal_tag_repository.get_by_entry(entry_id)}
        new_tags = [t for t in tag_names if t not in existing]
        if not new_tags:
            return []

        return self.journal_tag_repository.bulk_create(
            user_id=user_id, journal_entry_id=entry_id, tag_names=new_tags
        )

    def get_entries(self, user_id: UUID) -> list[dict]:
        entries = self.journal_entry_repository.get_by_user(user_id)
        result = []
        for entry in entries:
            tags = self.journal_tag_repository.get_by_entry(entry.id)
            result.append({"entry": entry, "tags": tags})
        return result

    def get_entry_detail(self, user_id: UUID, entry_id: UUID) -> dict | None:
        entry = self.journal_entry_repository.get_by_id_and_user(entry_id, user_id)
        if not entry:
            return None
        tags = self.journal_tag_repository.get_by_entry(entry.id)
        return {"entry": entry, "tags": tags}

    def delete_entry(self, user_id: UUID, entry_id: UUID) -> bool:
        """FR-JRN-03: user-delete cascades transcript + tags. Soft-deletes
        the entry (matches journal_entries.is_deleted) and hard-deletes
        its tags (no soft-delete column exists on journal_tags)."""
        entry = self.journal_entry_repository.get_by_id_and_user(entry_id, user_id)
        if not entry:
            return False
        self.journal_tag_repository.delete_by_entry(entry_id)
        self.journal_entry_repository.soft_delete(entry)
        return True
