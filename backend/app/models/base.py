import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Column, String, Table, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# Read-only mapping onto Supabase's auth.users — this app never writes to
# it (Supabase Auth owns that table). email/created_at are real columns
# Supabase already provides; mapped here (Phase 14) purely so the admin
# user list can show an identifying email instead of a bare UUID, without
# a raw-SQL query.
auth_users = Table(
    "users",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("email", String, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True), nullable=True),
    schema="auth",
)


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
