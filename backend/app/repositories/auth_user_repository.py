import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import auth_users


class AuthUserRepository:
    """
    Read-only queries against Supabase's auth.users (via the auth_users
    Table in app.models.base) — never a full ORM repository since this app
    never writes to that table.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list:
        return self.db.execute(
            select(auth_users).order_by(auth_users.c.created_at.desc())
        ).all()

    def get_by_id(self, user_id: uuid.UUID):
        return self.db.execute(
            select(auth_users).where(auth_users.c.id == user_id)
        ).first()
