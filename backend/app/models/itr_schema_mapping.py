from datetime import datetime, timezone

from sqlalchemy import Boolean, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ItrSchemaMapping(UUIDMixin, TimestampMixin, Base):
    """
    One assessment year's CBDT ITR-3 field-name mapping — the schema-driven
    layer FR-AIS-05 needs so a new AY's official field names can be added
    via the Admin Panel (POST /admin/itr-schemas) without a code deploy.
    ITR3ExportService reads mapping_json to know which CBDT field names to
    emit; it never hardcodes them.
    """

    __tablename__ = "itr_schema_mappings"

    ay: Mapped[str] = mapped_column(
        String(9),
        nullable=False,
        unique=True,
        index=True,
    )
    schema_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    mapping_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
