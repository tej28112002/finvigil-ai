from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.models.user_tax_persona import UserTaxPersona


def _get_role(db: Session, user_id: UUID) -> str:
    persona = (
        db.query(UserTaxPersona)
        .filter(UserTaxPersona.user_id == user_id)
        .first()
    )
    return persona.role if persona else "user"


def get_current_admin_user_id(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> UUID:
    """
    FastAPI dependency: verifies the authenticated user has
    user_tax_personas.role = 'admin'. No row for the user (never visited
    /settings, or never granted a role) defaults to 'user' — both raise
    403, never a 500 or a silent pass-through.

    Phase 14: role replaces the original is_admin boolean as the
    authoritative check (is_admin is kept on the table, unread, for
    history — see UserTaxPersona's docstring).
    """
    if _get_role(db, user_id) != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user_id


def get_current_support_or_admin_user_id(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> UUID:
    """
    Broader gate for read-only support tooling (impersonation-view, broker
    resync-on-behalf-of) — allows 'support' role in addition to 'admin'.
    Full admin actions (role changes, feature flags) stay on
    get_current_admin_user_id above, admin-only.
    """
    if _get_role(db, user_id) not in ("support", "admin"):
        raise HTTPException(status_code=403, detail="Admin or support access required.")
    return user_id
