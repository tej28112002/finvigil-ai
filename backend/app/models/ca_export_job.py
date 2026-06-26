import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class CaExportJob(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ca_export_jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        ENUM(
            "pending", "processing", "completed", "failed",
            name="job_status_enum",
            create_type=False,
        ),
        nullable=False,
        server_default="pending",
    )
    s3_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    assessment_year: Mapped[str | None] = mapped_column(
        String(9),
        nullable=True,
    )
    export_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
