from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "finvigil",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.grace_period_tasks",
        "app.tasks.harvest_tasks",
    ],
)

# crontab's "now" resolves through app.timezone (verified against celery's
# own schedules.py source) — so crontab(hour=6) below genuinely fires at
# 06:00 IST wall-clock, not 06:00 UTC. Do not remove this setting or the
# BRD's FR-HAR-03 "06:00 IST" requirement silently becomes 06:00 UTC
# (11:30 IST).
celery_app.conf.timezone = "Asia/Kolkata"
celery_app.conf.enable_utc = True

celery_app.conf.beat_schedule = {
    # Proactive version of SubscriptionService.reconcile_expired_grace(),
    # which until now only ran lazily from GET /billing/subscription (BRD
    # §10: "After day 7: downgrade to Free"). Hourly rather than pinned to
    # a specific time — unlike the harvest job, nothing in the BRD ties
    # this to a particular clock time, and the grace window is
    # day-granular anyway so hourly is far more than sufficient.
    "reconcile-expired-grace-hourly": {
        "task": "app.tasks.grace_period_tasks.reconcile_expired_grace_task",
        "schedule": crontab(minute=0),
    },
    # FR-HAR-03: "Pro/Premium — 06:00 IST Celery job". Portfolio-change and
    # 60s-polling triggers from the same FR are not part of this task —
    # only the daily scheduled scan.
    "daily-harvest-scan-0600-ist": {
        "task": "app.tasks.harvest_tasks.daily_harvest_scan_task",
        "schedule": crontab(hour=6, minute=0),
    },
}
