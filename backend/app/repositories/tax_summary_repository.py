import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.tax_summary import TaxSummary
from app.repositories.base import BaseRepository


class TaxSummaryRepository(BaseRepository[TaxSummary]):
    def __init__(self, db: Session):
        super().__init__(db, TaxSummary)

    def get_by_user_and_year(
        self,
        user_id: uuid.UUID,
        assessment_year: str,
    ) -> TaxSummary | None:
        return (
            self.db.query(TaxSummary)
            .filter(
                TaxSummary.user_id == user_id,
                TaxSummary.assessment_year == assessment_year,
            )
            .first()
        )

    def get_all_by_user(
        self,
        user_id: uuid.UUID,
    ) -> list[TaxSummary]:
        return (
            self.db.query(TaxSummary)
            .filter(TaxSummary.user_id == user_id)
            .order_by(TaxSummary.assessment_year.desc())
            .all()
        )

    def upsert_tax_summary(
        self,
        user_id: uuid.UUID,
        assessment_year: str,
        total_stcg_gains: float,
        total_ltcg_gains: float,
        stcg_tax_rate: float,
        ltcg_tax_rate: float,
        ltcg_exemption: float,
        taxable_stcg: float,
        taxable_ltcg: float,
        stcg_tax: float,
        ltcg_tax: float,
        total_tax_liability: float,
    ) -> TaxSummary:
        existing = self.get_by_user_and_year(user_id, assessment_year)

        if existing:
            existing.total_stcg_gains = total_stcg_gains
            existing.total_ltcg_gains = total_ltcg_gains
            existing.stcg_tax_rate = stcg_tax_rate
            existing.ltcg_tax_rate = ltcg_tax_rate
            existing.ltcg_exemption = ltcg_exemption
            existing.taxable_stcg = taxable_stcg
            existing.taxable_ltcg = taxable_ltcg
            existing.stcg_tax = stcg_tax
            existing.ltcg_tax = ltcg_tax
            existing.total_tax_liability = total_tax_liability
            existing.calculated_at = datetime.now(timezone.utc)
            self.db.flush()
            self.db.refresh(existing)
            return existing

        return self.create(
            user_id=user_id,
            assessment_year=assessment_year,
            total_stcg_gains=total_stcg_gains,
            total_ltcg_gains=total_ltcg_gains,
            stcg_tax_rate=stcg_tax_rate,
            ltcg_tax_rate=ltcg_tax_rate,
            ltcg_exemption=ltcg_exemption,
            taxable_stcg=taxable_stcg,
            taxable_ltcg=taxable_ltcg,
            stcg_tax=stcg_tax,
            ltcg_tax=ltcg_tax,
            total_tax_liability=total_tax_liability,
        )