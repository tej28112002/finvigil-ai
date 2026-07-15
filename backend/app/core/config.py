import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Settings:
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
    ZERODHA_API_KEY: str = os.environ.get("ZERODHA_API_KEY", "")
    ZERODHA_API_SECRET: str = os.environ.get("ZERODHA_API_SECRET", "")
    SUPABASE_URL: str = os.environ.get(
        "SUPABASE_URL", "https://ozbzbesayaxmptsyaznb.supabase.co"
    )

    # Phase 12 — Razorpay billing. All empty until an admin sets up a
    # Razorpay account and pastes TEST-mode credentials here — see the
    # TODO comments in backend/.env. Never put live/production keys in
    # this file or in .env under version control.
    RAZORPAY_KEY_ID: str = os.environ.get("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.environ.get("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET: str = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
    RAZORPAY_PLAN_PRO_MONTHLY: str = os.environ.get("RAZORPAY_PLAN_PRO_MONTHLY", "")
    RAZORPAY_PLAN_PRO_ANNUAL: str = os.environ.get("RAZORPAY_PLAN_PRO_ANNUAL", "")
    RAZORPAY_PLAN_PREMIUM_MONTHLY: str = os.environ.get("RAZORPAY_PLAN_PREMIUM_MONTHLY", "")
    RAZORPAY_PLAN_PREMIUM_ANNUAL: str = os.environ.get("RAZORPAY_PLAN_PREMIUM_ANNUAL", "")


settings = Settings()

