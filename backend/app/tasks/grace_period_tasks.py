import logging

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger("finvigil.tasks")


@celery_app.task(name="app.tasks.grace_period_tasks.reconcile_expired_grace_task")
def reconcile_expired_grace_task() -> None:
    """
    Proactive counterpart to SubscriptionService.reconcile_expired_grace(),
    which until Phase 12b only ran lazily from GET /billing/subscription.
    Runs hourly (see celery_app.beat_schedule). Reuses the existing service
    method rather than reimplementing the grace-window state machine —
    only the candidate selection (list_grace_eligible) and the
    commit/rollback-per-run boundary are new here, since Celery tasks run
    outside FastAPI's Depends(get_db) and must manage that themselves.
    """
    db = SessionLocal()
    try:
        repository = SubscriptionRepository(db)
        service = SubscriptionService(repository)

        candidates = repository.list_grace_eligible()
        downgraded = 0
        for subscription in candidates:
            plan_before = subscription.plan_id
            service.reconcile_expired_grace(subscription.user_id)
            if subscription.plan_id != plan_before:
                downgraded += 1

        db.commit()
        logger.info(
            "Grace reconciliation: checked=%d downgraded=%d",
            len(candidates),
            downgraded,
        )
    except Exception:
        db.rollback()
        logger.exception("Grace reconciliation task failed")
        raise
    finally:
        db.close()
