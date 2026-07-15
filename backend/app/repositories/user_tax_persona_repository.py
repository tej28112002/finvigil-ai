import uuid

from sqlalchemy.orm import Session

from app.models.user_tax_persona import UserTaxPersona
from app.repositories.base import BaseRepository


class UserTaxPersonaRepository(BaseRepository[UserTaxPersona]):
    def __init__(self, db: Session):
        super().__init__(db, UserTaxPersona)

    def get_by_user(self, user_id: uuid.UUID) -> UserTaxPersona | None:
        return (
            self.db.query(UserTaxPersona)
            .filter(UserTaxPersona.user_id == user_id)
            .first()
        )

    def get_or_create(self, user_id: uuid.UUID) -> UserTaxPersona:
        persona = self.get_by_user(user_id)
        if persona:
            return persona
        instance = UserTaxPersona(user_id=user_id)
        self.db.add(instance)
        self.db.flush()
        self.db.refresh(instance)
        return instance

    def get_all(self) -> list[UserTaxPersona]:
        return self.db.query(UserTaxPersona).all()

    def update_role(self, persona: UserTaxPersona, role: str) -> UserTaxPersona:
        persona.role = role
        self.db.flush()
        self.db.refresh(persona)
        return persona
