from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.models.user_tax_persona import UserTaxPersona


def get_current_admin_user_id(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> UUID:
    """
    FastAPI dependency: verifies the authenticated user also has
    user_tax_personas.is_admin = TRUE. No row for the user (never visited
    /settings, or never granted admin) is treated the same as is_admin =
    FALSE — both raise 403, never a 500 or a silent pass-through.
    """
    persona = (
        db.query(UserTaxPersona)
        .filter(UserTaxPersona.user_id == user_id)
        .first()
    )
    if not persona or not persona.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user_id
