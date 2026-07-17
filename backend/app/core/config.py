import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Settings:
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

    # Phase 16 -- BYOK broker credentials. Each user's own Zerodha/Upstox/
    # Groww api_key + api_secret now live on broker_connections (api_key
    # plain, secrets in Vault) -- no more global ZERODHA_API_KEY/SECRET.
    # This secret signs the short-lived OAuth callback "state" param so
    # brokers' unauthenticated redirect-back endpoints can't be handed an
    # arbitrary user_id (see app/core/oauth_state.py).
    OAUTH_STATE_SECRET: str = os.environ.get("OAUTH_STATE_SECRET", "")

    SUPABASE_URL: str = os.environ.get(
        "SUPABASE_URL", "https://ozbzbesayaxmptsyaznb.supabase.co"
    )

    # Phase 16 -- where broker OAuth callbacks (e.g. /brokers/zerodha/callback,
    # hit by a raw browser redirect from the broker, not an API call) send
    # the user's browser back to after completing the exchange. Mirrors the
    # frontend's own NEXT_PUBLIC_API_URL pointing the other direction.
    FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    # Phase 16 -- this backend's own public base URL (including /api/v1),
    # needed for brokers whose OAuth authorize step requires an exact
    # redirect_uri to be embedded in both the login URL and the token
    # exchange (Upstox). Must match NEXT_PUBLIC_API_URL, the frontend's
    # equivalent pointing the other direction -- and must match the
    # Redirect URI the user registers on their own broker app.
    BACKEND_URL: str = os.environ.get("BACKEND_URL", "http://localhost:8000/api/v1")

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

    # Phase 10 — Voice Journal STT (Groq Whisper-compatible API). Empty
    # until an admin pastes a real key from console.groq.com.
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")

    # Phase 12b — Celery broker/result backend. Upstash requires TLS, so
    # this MUST be rediss:// not redis:// (kombu's Redis transport only
    # switches to redis.SSLConnection on the "rediss" scheme — verified
    # against kombu's source, not assumed).
    REDIS_URL: str = os.environ.get("REDIS_URL", "")

    # Lightweight-deploy CORS allowlist. Defaults to local dev only, so
    # nothing changes for existing local setups unless this is explicitly
    # set. Comma-separated, no spaces — e.g.
    # "https://finvigil.vercel.app,https://finvigil-git-main.vercel.app"
    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.environ.get(
            "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]


settings = Settings()

