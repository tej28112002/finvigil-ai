import uuid
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, db: Session, model: type[T]):
        self.db = db
        self.model = model

    def get_by_id(self, id: uuid.UUID) -> T | None:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def create(self, **kwargs) -> T:
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def delete(self, instance: T) -> None:
        self.db.delete(instance)
        self.db.commit()
