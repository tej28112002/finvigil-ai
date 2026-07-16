from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from app.core.tax_utils import get_ay_date_range
from app.repositories.harvest_run_repository import HarvestRunRepository
from app.services.harvesting_service import HarvestingService

ZERO = Decimal("0")
IST_OFFSET = timedelta(hours=5, minutes=30)
DAILY_JOB_HOUR_IST = 6
LTCG_HOLDING_DAYS_THRESHOLD = 365  # must match HarvestingService exactly


def _last_scheduled_run_boundary_utc(now_utc: datetime) -> datetime:
    """
    UTC instant of the most recent 06:00 IST — the daily harvest job's
    schedule (FR-HAR-03). A cached run is "fresh" iff it was created at or
    after this boundary, so cache validity tracks the job's actual
    schedule instead of a flat "N hours old" guess.
    """
    now_ist = now_utc + IST_OFFSET
    boundary_ist = now_ist.replace(
        hour=DAILY_JOB_HOUR_IST, minute=0, second=0, microsecond=0
    )
    if boundary_ist > now_ist:
        boundary_ist -= timedelta(days=1)
    return boundary_ist - IST_OFFSET


class HarvestCacheService:
    """
    Pro/Premium-only read-through cache in front of HarvestingService's
    pure computation, backed by the harvest_runs / harvest_recommendation_
    lines tables (already deployed in db/schema.sql per BRD §14, never
    wired to app code until Phase 12b). Free tier must keep calling
    HarvestingService directly — FR-HAR-03: "Free on-demand only" — and
    never touches this class.

    Read path: if a completed run exists since the last 06:00 IST
    boundary, serve it (no live price fetch). Otherwise compute live via
    HarvestingService and persist a fresh run — covers first-ever call for
    a user before the daily job has run yet, and a failed prior run.
    """

    def __init__(
        self,
        harvesting_service: HarvestingService,
        harvest_run_repository: HarvestRunRepository,
    ):
        self.harvesting_service = harvesting_service
        self.harvest_run_repository = harvest_run_repository

    def refresh(self, user_id: UUID, assessment_year: str):
        """
        Always computes live and persists a new run — used by the daily
        Celery job (which wants a fresh scan regardless of what's cached)
        and by the read path's cache-miss fallback.
        """
        run = self.harvest_run_repository.create_run(user_id, assessment_year)
        try:
            candidates = self.harvesting_service.get_harvest_candidates(
                user_id=user_id, assessment_year=assessment_year
            )
        except Exception:
            self.harvest_run_repository.mark_failed(run)
            raise

        self.harvest_run_repository.add_recommendation_lines(
            harvest_run_id=run.id, user_id=user_id, candidates=candidates
        )
        total_tax_saved_estimate = sum(
            (c["estimated_tax_saving"] for c in candidates), ZERO
        )
        return self.harvest_run_repository.mark_completed(
            run, total_tax_saved_estimate=total_tax_saved_estimate
        )

    def _get_fresh_run(self, user_id: UUID, assessment_year: str):
        boundary = _last_scheduled_run_boundary_utc(datetime.now(timezone.utc))
        run = self.harvest_run_repository.get_latest_completed(
            user_id=user_id, assessment_year=assessment_year, since=boundary
        )
        return run or self.refresh(user_id, assessment_year)

    def _candidate_dicts(self, run) -> list[dict]:
        now = datetime.now(timezone.utc)
        lines = self.harvest_run_repository.get_recommendation_lines(run.id)
        candidates = []
        for line in lines:
            lot = line.holding_lot
            holding_period_days = (now - lot.buy_date).days
            gain_type = (
                "LTCG"
                if holding_period_days > LTCG_HOLDING_DAYS_THRESHOLD
                else "STCG"
            )
            candidates.append(
                {
                    "lot_id": lot.id,
                    "instrument_id": lot.instrument_id,
                    "symbol": lot.instrument.symbol,
                    "quantity": line.quantity_to_sell,
                    "buy_price": lot.buy_price,
                    "buy_date": lot.buy_date,
                    # Exact arithmetic reconstruction, no live price fetch:
                    # simulated_stcg_ltcg == (current_price - buy_price) *
                    # qty, so current_value == buy_price*qty + that delta.
                    "current_value": (
                        Decimal(str(lot.buy_price)) * line.quantity_to_sell
                        + line.simulated_stcg_ltcg
                    ),
                    # Always False by construction — see
                    # HarvestRecommendationLine's docstring.
                    "is_price_estimate": False,
                    "unrealized_loss": line.simulated_stcg_ltcg,
                    "holding_period_days": holding_period_days,
                    "gain_type": gain_type,
                    "estimated_tax_saving": line.savings_amount,
                }
            )
        candidates.sort(key=lambda c: c["estimated_tax_saving"], reverse=True)
        return candidates

    def get_harvest_candidates(
        self, user_id: UUID, assessment_year: str
    ) -> list[dict]:
        run = self._get_fresh_run(user_id, assessment_year)
        return self._candidate_dicts(run)

    def get_harvest_summary(self, user_id: UUID, assessment_year: str) -> dict:
        run = self._get_fresh_run(user_id, assessment_year)
        candidates = self._candidate_dicts(run)

        total_harvestable_loss = sum(
            (c["unrealized_loss"] for c in candidates), ZERO
        )
        total_estimated_tax_saving = sum(
            (c["estimated_tax_saving"] for c in candidates), ZERO
        )

        _, ay_end = get_ay_date_range(assessment_year)
        march_31 = ay_end - timedelta(days=1)
        days_until_march_31 = max(
            0, (march_31.date() - datetime.now(timezone.utc).date()).days
        )

        return {
            "assessment_year": assessment_year,
            "total_harvestable_loss": total_harvestable_loss,
            "total_estimated_tax_saving": total_estimated_tax_saving,
            "candidate_count": len(candidates),
            "days_until_march_31": days_until_march_31,
        }
