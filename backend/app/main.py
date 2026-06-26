from fastapi import FastAPI
from app.api.v1 import health, broker, trade, holding, dashboard, portfolio, realized_gain, tax, tax_export, corporate_action, csv_import, zerodha

app = FastAPI(title="FinVigil AI Backend")

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