import uuid

from sqlalchemy.orm import Session

from app.models.journal_entry import JournalEntry
from app.repositories.base import BaseRepository


class JournalEntryRepository(BaseRepository[JournalEntry]):
    def __init__(self, db: Session):
        super().__init__(db, JournalEntry)

    def create_entry(self, user_id: uuid.UUID, transcript: str) -> JournalEntry:
        return self.create(user_id=user_id, transcript=transcript)

    def get_by_id_and_user(
        self, entry_id: uuid.UUID, user_id: uuid.UUID
    ) -> JournalEntry | None:
        return (
            self.db.query(JournalEntry)
            .filter(
                JournalEntry.id == entry_id,
                JournalEntry.user_id == user_id,
                JournalEntry.is_deleted.is_(False),
            )
            .first()
        )

    def get_by_user(self, user_id: uuid.UUID) -> list[JournalEntry]:
        return (
            self.db.query(JournalEntry)
            .filter(
                JournalEntry.user_id == user_id,
                JournalEntry.is_deleted.is_(False),
            )
            .order_by(JournalEntry.created_at.desc())
            .all()
        )

    def soft_delete(self, entry: JournalEntry) -> None:
        entry.is_deleted = True
        self.db.flush()
        self.db.refresh(entry)
