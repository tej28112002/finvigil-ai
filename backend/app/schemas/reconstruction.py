from uuid import UUID

from pydantic import BaseModel


class ReconstructionResultResponse(BaseModel):
    user_id: UUID
    realized_gains_deleted: int
    holding_lots_deleted: int
    holding_lots_created: int
    realized_gains_created: int
    corporate_actions_reapplied: int
    lots_adjusted_by_corporate_actions: int
