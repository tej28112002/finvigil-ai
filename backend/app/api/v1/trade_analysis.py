import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.trade_analysis_repository import TradeAnalysisRepository
from app.repositories.trade_repository import TradeRepository
from app.services.trade_analysis_pipeline import TradeAnalysisPipeline
from app.services.trade_llm_service import TradeLLMService

logger = logging.getLogger("finvigil")

router = APIRouter()


class RunAnalysisRequest(BaseModel):
    week_start: date | None = None
    week_end: date | None = None


def get_pipeline(db: Session = Depends(get_db)) -> TradeAnalysisPipeline:
    return TradeAnalysisPipeline(
        trade_repository=TradeRepository(db),
        realized_gain_repository=RealizedGainRepository(db),
        trade_analysis_repository=TradeAnalysisRepository(db),
        trade_llm_service=TradeLLMService(),
    )


def get_trade_analysis_repository(db: Session = Depends(get_db)) -> TradeAnalysisRepository:
    return TradeAnalysisRepository(db)


@router.post("/journal/analyze")
def analyze_trades(
    request: RunAnalysisRequest | None = None,
    user_id: UUID = Depends(get_current_user_id),
    pipeline: TradeAnalysisPipeline = Depends(get_pipeline),
):
    logger.info(f"[FINVIGIL] Starting weekly trade analysis for user {user_id}")
    week_start = request.week_start if request else None
    week_end = request.week_end if request else None
    result = pipeline.run_weekly_analysis(
        user_id=user_id, week_start=week_start, week_end=week_end
    )
    logger.info(
        f"[FINVIGIL] Weekly trade analysis for user {user_id} finished with status "
        f"{result.get('status')}"
    )
    return result


@router.get("/journal/analysis/latest")
def get_latest_analysis(
    user_id: UUID = Depends(get_current_user_id),
    repository: TradeAnalysisRepository = Depends(get_trade_analysis_repository),
):
    analysis = repository.get_latest_by_user(user_id)
    if not analysis:
        return {"status": "no_analysis"}
    return {
        "id": str(analysis.id),
        "week_start": str(analysis.week_start),
        "week_end": str(analysis.week_end),
        "trade_count": analysis.trade_count,
        "analysis_type": analysis.analysis_type,
        "analysis": analysis.analysis_json,
        "created_at": analysis.created_at,
    }


@router.get("/journal/analysis/history")
def get_analysis_history(
    user_id: UUID = Depends(get_current_user_id),
    repository: TradeAnalysisRepository = Depends(get_trade_analysis_repository),
):
    analyses = repository.get_by_user(user_id, limit=20)
    return [
        {
            "id": str(a.id),
            "week_start": str(a.week_start),
            "week_end": str(a.week_end),
            "grade": (a.analysis_json or {}).get("grade", "N/A"),
            "trade_count": a.trade_count,
            "analysis_type": a.analysis_type,
            "created_at": a.created_at,
        }
        for a in analyses
    ]


@router.get("/journal/analysis/{analysis_id}")
def get_analysis_by_id(
    analysis_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: TradeAnalysisRepository = Depends(get_trade_analysis_repository),
):
    analysis = repository.get_by_id_and_user(analysis_id, user_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found.")
    return analysis.analysis_json


@router.post("/journal/compare")
def compare_analyses(
    user_id: UUID = Depends(get_current_user_id),
    pipeline: TradeAnalysisPipeline = Depends(get_pipeline),
):
    result = pipeline.run_comparison(user_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Not enough analysis history to run a comparison yet.",
        )
    return result
