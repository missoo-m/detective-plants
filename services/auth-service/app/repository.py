import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .models import Role, User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def _base_query(self):
        return select(User).options(joinedload(User.role), joinedload(User.profile))

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = self._base_query().where(User.id == user_id)
        return self.session.scalars(stmt).first()

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = self._base_query().where(User.email == email)
        return self.session.scalars(stmt).first()

    def list_users(self, role: Optional[str] = None, status: Optional[str] = None) -> list[User]:
        stmt = self._base_query()
        if role:
            stmt = stmt.join(User.role).where(Role.name == role)
        if status:
            stmt = stmt.where(User.status == status)
        stmt = stmt.order_by(User.created_at, User.email)
        return list(self.session.scalars(stmt).unique().all())
