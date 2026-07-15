import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.monte_carlo_run import MonteCarloRun
from app.repositories.base import BaseRepository


class MonteCarloRunRepository(BaseRepository[MonteCarloRun]):
    def __init__(self, db: Session):
        super().__init__(db, MonteCarloRun)

    def create_run(
        self,
        user_id: uuid.UUID,
        replay_scenario_id: Optional[uuid.UUID],
        parameters: dict,
        status: str,
        result_data: Optional[dict],
    ) -> MonteCarloRun:
        return self.create(
            user_id=user_id,
            replay_scenario_id=replay_scenario_id,
            parameters=parameters,
            status=status,
            result_data=result_data,
        )

    def update_result(
        self,
        run: MonteCarloRun,
        status: str,
        result_data: Optional[dict],
    ) -> MonteCarloRun:
        run.status = status
        run.result_data = result_data
        self.db.flush()
        self.db.refresh(run)
        return run

    def get_by_id_and_user(
        self,
        run_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MonteCarloRun | None:
        return (
            self.db.query(MonteCarloRun)
            .filter(
                MonteCarloRun.id == run_id,
                MonteCarloRun.user_id == user_id,
            )
            .first()
        )

    def get_by_user(self, user_id: uuid.UUID) -> list[MonteCarloRun]:
        return (
            self.db.query(MonteCarloRun)
            .filter(MonteCarloRun.user_id == user_id)
            .order_by(MonteCarloRun.created_at.desc())
            .all()
        )
