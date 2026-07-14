import uuid

from sqlalchemy.orm import Session

from app.models.replay_run import ReplayRun
from app.models.replay_scenario import ReplayScenario
from app.repositories.base import BaseRepository


class ReplayScenarioRepository(BaseRepository[ReplayScenario]):
    def __init__(self, db: Session):
        super().__init__(db, ReplayScenario)

    def create_scenario(
        self,
        user_id: uuid.UUID,
        name: str,
        parameters: dict,
    ) -> ReplayScenario:
        return self.create(
            user_id=user_id,
            name=name,
            parameters=parameters,
        )

    def get_by_id_and_user(
        self,
        scenario_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ReplayScenario | None:
        """
        Ownership-scoped single-scenario lookup. A mismatched owner and a
        genuinely nonexistent scenario both fall through to the same None
        result — same pattern as HoldingLotRepository.get_by_id_and_user.
        """
        return (
            self.db.query(ReplayScenario)
            .filter(
                ReplayScenario.id == scenario_id,
                ReplayScenario.user_id == user_id,
            )
            .first()
        )

    def get_by_user(self, user_id: uuid.UUID) -> list[ReplayScenario]:
        return (
            self.db.query(ReplayScenario)
            .filter(ReplayScenario.user_id == user_id)
            .order_by(ReplayScenario.created_at.desc())
            .all()
        )


class ReplayRunRepository(BaseRepository[ReplayRun]):
    def __init__(self, db: Session):
        super().__init__(db, ReplayRun)

    def create_run(
        self,
        user_id: uuid.UUID,
        replay_scenario_id: uuid.UUID,
        result_data: dict,
    ) -> ReplayRun:
        return self.create(
            user_id=user_id,
            replay_scenario_id=replay_scenario_id,
            result_data=result_data,
        )

    def get_by_id_and_user(
        self,
        run_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ReplayRun | None:
        return (
            self.db.query(ReplayRun)
            .filter(
                ReplayRun.id == run_id,
                ReplayRun.user_id == user_id,
            )
            .first()
        )

    def get_by_scenario(
        self,
        scenario_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[ReplayRun]:
        return (
            self.db.query(ReplayRun)
            .filter(
                ReplayRun.replay_scenario_id == scenario_id,
                ReplayRun.user_id == user_id,
            )
            .order_by(ReplayRun.created_at.desc())
            .all()
        )
