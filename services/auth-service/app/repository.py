import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from .models import Role, User

SORT_COLUMNS = {"created_at": User.created_at, "name": User.name, "email": User.email}


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def _base_query(self):
        return select(User).options(joinedload(User.role), joinedload(User.profile))

    def add(self, user: User) -> None:
        self.session.add(user)

    def get_role(self, name: str) -> Optional[Role]:
        return self.session.scalars(select(Role).where(Role.name == name)).first()

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.session.scalars(self._base_query().where(User.id == user_id)).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.scalars(self._base_query().where(User.email == email)).first()

    def list_users(self, role: Optional[str] = None, status: Optional[str] = None,
                   search: Optional[str] = None, sort_by: str = "created_at",
                   descending: bool = False, limit: Optional[int] = None, offset: int = 0) -> list[User]:
        stmt = self._base_query()
        if role:
            stmt = stmt.join(User.role).where(Role.name == role)
        if status:
            stmt = stmt.where(User.status == status)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(or_(User.name.ilike(like), User.email.ilike(like)))
        column = SORT_COLUMNS[sort_by]
        stmt = stmt.order_by(column.desc() if descending else column.asc(), User.email)
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).unique().all())

    def count_by_role(self) -> dict:
        stmt = select(Role.name, func.count(User.id)).join(User, User.role_id == Role.id).group_by(Role.name)
        return {name: count for name, count in self.session.execute(stmt).all()}

    def count_by_status(self) -> dict:
        stmt = select(User.status, func.count(User.id)).group_by(User.status)
        return {status: count for status, count in self.session.execute(stmt).all()}
