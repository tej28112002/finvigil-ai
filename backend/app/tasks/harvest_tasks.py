import logging
from datetime import datetime, timezone

from app.core.celery_app import celery_app
from app.core.tax_utils import get_assessment_year
from app.db.session import SessionLocal
from app.repositories.broker_connection_repository import BrokerConnectionRepository
from app.repositories.harvest_run_repository import HarvestRunRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.vault_repository import VaultRepository
from app.services.harvest_cache_service import HarvestCacheService
from app.services.harvesting_service import HarvestingService
from app.services.price_service import PriceService
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger("finvigil.tasks")


@celery_app.task(name="app.tasks.harvest_tasks.daily_harvest_scan_task")
def daily_harvest_scan_task() -> None:
    """
    FR-HAR-03: "Pro/Premium — 06:00 IST Celery job". Computes and persists
    a fresh harvest_runs row (via HarvestCacheService.refresh, same code
    path the API's cache-miss fallback uses) for every currently
    Pro-or-Premium user, current AY only — harvesting a loss in an
    already-closed AY isn't meaningful, so past AYs (Premium's multi-AY
    history) are intentionally not scanned here.

    Pro/Premium selection reuses SubscriptionService.
    compute_effective_entitlement (the same grace-window-aware logic every
    Pro-gated endpoint uses) rather than a separate SQL filter, so this
    task can never disagree with what check_subscription_tier() would say
    for the same user at the same moment.

    Commits per-user, not once at the end — one user's failure (e.g. a
    price-fetch error) must not roll back already-persisted runs for
    every other user scanned earlier in the same loop.
    """
    db = SessionLocal()
    try:
        subscription_repository = SubscriptionRepository(db)
        subscription_service = SubscriptionService(subscription_repository)

        pro_premium_user_ids = [
            subscription.user_id
            for subscription in subscription_repository.get_all()
            if subscription_service.compute_effective_entitlement(subscription)[
                "is_pro_or_premium"
            ]
        ]

        holding_repository = HoldingLotRepository(db)
        realized_gain_repository = RealizedGainRepository(db)
        broker_repository = BrokerConnectionRepository(db)
        vault_repository = VaultRepository(db)
        price_service = PriceService(
            broker_connection_repository=broker_repository,
            vault_repository=vault_repository,
        )
        harvesting_service = HarvestingService(
            holding_repository=holding_repository,
            realized_gain_repository=realized_gain_repository,
            price_service=price_service,
        )
        cache_service = HarvestCacheService(
            harvesting_service=harvesting_service,
            harvest_run_repository=HarvestRunRepository(db),
        )

        assessment_year = get_assessment_year(datetime.now(timezone.utc))
        succeeded, failed = 0, 0
        for user_id in pro_premium_user_ids:
            try:
                cache_service.refresh(user_id, assessment_year)
                db.commit()
                succeeded += 1
            except Exception:
                db.rollback()
                logger.exception(
                    "Daily harvest scan failed for user_id=%s", user_id
                )
                failed += 1

        logger.info(
            "Daily harvest scan: users=%d succeeded=%d failed=%d ay=%s",
            len(pro_premium_user_ids),
            succeeded,
            failed,
            assessment_year,
        )
    finally:
        db.close()
