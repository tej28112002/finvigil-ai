import uuid

from sqlalchemy.orm import Session, joinedload

from app.models.backtest import BacktestLeg, BacktestRun, BacktestStrategy


class BacktestRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── strategy CRUD ────────────────────────────────────────────────────

    def create_strategy(self, user_id: uuid.UUID, **fields) -> BacktestStrategy:
        strategy = BacktestStrategy(user_id=user_id, **fields)
        self.db.add(strategy)
        self.db.flush()
        self.db.refresh(strategy)
        return strategy

    def get_strategy(
        self, id: uuid.UUID, user_id: uuid.UUID
    ) -> BacktestStrategy | None:
        return (
            self.db.query(BacktestStrategy)
            .options(joinedload(BacktestStrategy.legs))
            .filter(
                BacktestStrategy.id == id,
                BacktestStrategy.user_id == user_id,
            )
            .first()
        )

    def list_strategies(self, user_id: uuid.UUID) -> list[BacktestStrategy]:
        return (
            self.db.query(BacktestStrategy)
            .filter(BacktestStrategy.user_id == user_id)
            .order_by(BacktestStrategy.updated_at.desc())
            .all()
        )

    def update_strategy(self, strategy: BacktestStrategy, **fields) -> BacktestStrategy:
        for key, value in fields.items():
            setattr(strategy, key, value)
        self.db.flush()
        self.db.refresh(strategy)
        return strategy

    def delete_strategy(self, strategy: BacktestStrategy) -> None:
        self.db.delete(strategy)
        self.db.flush()

    # ── leg management ──────────────────────────────────────────────────

    def upsert_legs(
        self, strategy_id: uuid.UUID, legs: list[dict]
    ) -> list[BacktestLeg]:
        """Replaces every leg for this strategy wholesale: delete all
        existing legs, then re-create from the given list in order.
        Simpler and safer than diffing individual leg edits — the leg
        builder UI always submits the full leg list on save."""
        self.db.query(BacktestLeg).filter(
            BacktestLeg.strategy_id == strategy_id
        ).delete(synchronize_session=False)
        self.db.flush()

        created: list[BacktestLeg] = []
        for i, leg_fields in enumerate(legs, start=1):
            leg = BacktestLeg(strategy_id=strategy_id, leg_order=i, **leg_fields)
            self.db.add(leg)
            created.append(leg)
        self.db.flush()
        for leg in created:
            self.db.refresh(leg)
        return created

    # ── run management ──────────────────────────────────────────────────

    def create_run(self, strategy_id: uuid.UUID, user_id: uuid.UUID) -> BacktestRun:
        run = BacktestRun(strategy_id=strategy_id, user_id=user_id, status="pending")
        self.db.add(run)
        self.db.flush()
        self.db.refresh(run)
        return run

    def update_run(
        self,
        run: BacktestRun,
        status: str,
        result_json: dict | None = None,
        error: str | None = None,
    ) -> BacktestRun:
        run.status = status
        if result_json is not None:
            run.result_json = result_json
        if error is not None:
            run.error_message = error
        self.db.flush()
        self.db.refresh(run)
        return run

    def get_run(self, id: uuid.UUID, user_id: uuid.UUID) -> BacktestRun | None:
        return (
            self.db.query(BacktestRun)
            .filter(BacktestRun.id == id, BacktestRun.user_id == user_id)
            .first()
        )

    def list_runs(
        self, strategy_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[BacktestRun]:
        return (
            self.db.query(BacktestRun)
            .filter(
                BacktestRun.strategy_id == strategy_id,
                BacktestRun.user_id == user_id,
            )
            .order_by(BacktestRun.created_at.desc())
            .all()
        )
