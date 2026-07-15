import uuid

from sqlalchemy.orm import Session

from app.models.journal_tag import JournalTag
from app.repositories.base import BaseRepository


class JournalTagRepository(BaseRepository[JournalTag]):
    def __init__(self, db: Session):
        super().__init__(db, JournalTag)

    def bulk_create(
        self,
        user_id: uuid.UUID,
        journal_entry_id: uuid.UUID,
        tag_names: list[str],
    ) -> list[JournalTag]:
        instances = [
            JournalTag(
                user_id=user_id,
                journal_entry_id=journal_entry_id,
                tag_name=tag_name,
            )
            for tag_name in tag_names
        ]
        self.db.add_all(instances)
        self.db.flush()
        for instance in instances:
            self.db.refresh(instance)
        return instances

    def get_by_entry(self, journal_entry_id: uuid.UUID) -> list[JournalTag]:
        return (
            self.db.query(JournalTag)
            .filter(JournalTag.journal_entry_id == journal_entry_id)
            .all()
        )

    def delete_by_entry(self, journal_entry_id: uuid.UUID) -> int:
        """
        Hard delete — journal_tags has no is_deleted column (unlike
        journal_entries), and BRD FR-JRN-03 explicitly calls for tags to
        be fully removed ("cascades") on entry deletion, not just hidden.
        """
        deleted = (
            self.db.query(JournalTag)
            .filter(JournalTag.journal_entry_id == journal_entry_id)
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return deleted
