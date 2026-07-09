from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import health, broker, trade, holding, dashboard, portfolio, realized_gain, tax, tax_export, corporate_action, csv_import, zerodha, fno_pnl, reconstruction, crypto

app = FastAPI(title="FinVigil AI Backend")

# Phase 13 Stage 1 — allow the local Next.js dev server to call this API.
# Frontend attaches the Supabase-issued Bearer token; get_current_user_id()
# (Phase 11.2) verifies it on every protected route.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
app.include_router(fno_pnl.router, prefix="/api/v1")
app.include_router(reconstruction.router, prefix="/api/v1")
app.include_router(crypto.router, prefix="/api/v1")