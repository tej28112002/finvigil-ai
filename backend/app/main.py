import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import health, broker, trade, holding, dashboard, portfolio, realized_gain, tax, tax_export, corporate_action, csv_import, zerodha, upstox, groww, fno_pnl, reconstruction, crypto, harvesting, replay, monte_carlo, ais, admin_itr, billing, journal, admin
from app.core.config import settings

logger = logging.getLogger("finvigil")

app = FastAPI(title="FinVigil AI Backend")


# No handler existed before this: any unhandled exception (a transient DB
# error from Supabase's pooler dropping an idle connection, an unexpected
# data condition, anything) fell straight through to Starlette's bare
# default 500 with nothing logged anywhere — the exact reason a real 500
# reported from the frontend couldn't be traced back to a cause here.
# This doesn't change behavior for well-formed HTTPException responses
# (401/404/etc, handled separately by FastAPI already) — only for genuinely
# unexpected exceptions, which now get a full traceback in the server log
# and a clean, consistent JSON body instead of vanishing.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception on %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."},
    )

# Phase 13 Stage 1 — allow the local Next.js dev server to call this API.
# Frontend attaches the Supabase-issued Bearer token; get_current_user_id()
# (Phase 11.2) verifies it on every protected route.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(broker.router, prefix="/api/v1")
app.include_router(trade.router, prefix="/api/v1")
app.include_router(holding.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(realized_gain.router, prefix="/api/v1")
app.include_router(tax.router, prefix="/api/v1")
app.include_router(tax_export.router, prefix="/api/v1")
app.include_router(corporate_action.router, prefix="/api/v1")
app.include_router(csv_import.router, prefix="/api/v1")
app.include_router(zerodha.router, prefix="/api/v1")
app.include_router(upstox.router, prefix="/api/v1")
app.include_router(groww.router, prefix="/api/v1")
app.include_router(fno_pnl.router, prefix="/api/v1")
app.include_router(reconstruction.router, prefix="/api/v1")
app.include_router(crypto.router, prefix="/api/v1")
app.include_router(harvesting.router, prefix="/api/v1")
app.include_router(replay.router, prefix="/api/v1")
app.include_router(monte_carlo.router, prefix="/api/v1")
app.include_router(ais.router, prefix="/api/v1")
app.include_router(admin_itr.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(journal.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")