import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class TradeAnalysisResult(UUIDMixin, TimestampMixin, Base):
    """
    One LLM-generated trade analysis snapshot (AI Journaling). analysis_type
    is "weekly" for a single-period report or "comparison" for a
    week-over-week comparison (compared_with_id then points at the earlier
    "weekly" row it was compared against). Table already existed in
    Supabase before this model was written -- see
    db/migrations/007_trade_analysis.sql.
    """

    __tablename__ = "trade_analysis_results"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    trade_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    analysis_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="weekly"
    )
    analysis_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_llm_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    compared_with_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trade_analysis_results.id"),
        nullable=True,
    )
    llm_model: Mapped[str | None] = mapped_column(
        String(50), nullable=True, server_default="llama-3.3-70b-versatile"
    )
    prompt_version: Mapped[str | None] = mapped_column(
        String(10), nullable=True, server_default="v1"
    )
