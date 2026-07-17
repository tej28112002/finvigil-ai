from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.models.user_tax_persona import UserTaxPersona

router = APIRouter()


@router.get("/me")
def get_me(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    persona = (
        db.query(UserTaxPersona)
        .filter(UserTaxPersona.user_id == user_id)
        .first()
    )
    return {
        "user_id": str(user_id),
        "role": persona.role if persona else "user",
    }
