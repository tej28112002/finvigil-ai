import uuid

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class JournalEntry(UUIDMixin, TimestampMixin, Base):
    """
    One voice (or text) journal entry (BRD FR-JRN-*). Stores ONLY the
    transcript — raw audio is never persisted anywhere: JournalService
    transcribes an uploaded clip in memory and discards the bytes the
    moment the STT call returns, satisfying "delete raw audio within <5s
    of successful transcription" (BRD §6) with a much larger safety
    margin than 5 seconds, since it's simply never written to disk/DB in
    the first place.
    """

    __tablename__ = "journal_entries"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transcript: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
