from fastapi import FastAPI
from app.api.v1 import health, broker, trade, holding, dashboard, portfolio, realized_gain

app = FastAPI(title="FinVigil AI Backend")

app.include_router(health.router, prefix="/api/v1")
app.include_router(broker.router, prefix="/api/v1")
app.include_router(trade.router, prefix="/api/v1")
app.include_router(holding.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(realized_gain.router, prefix="/api/v1")
