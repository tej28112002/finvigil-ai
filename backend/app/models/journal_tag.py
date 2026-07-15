import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class JournalTag(UUIDMixin, TimestampMixin, Base):
    """
    One psychology tag on a JournalEntry. tag_name is plain VARCHAR at the
    DB level (no Postgres enum) — the "fixed psychology taxonomy" (BRD
    FR-JRN-02) is enforced in JournalService against
    app.core.journal_taxonomy.PSYCHOLOGY_TAGS, not by a DB constraint.
    """

    __tablename__ = "journal_tags"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
