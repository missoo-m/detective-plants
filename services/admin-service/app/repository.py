import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import ExpertApplication


class ApplicationRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, obj) -> None:
        self.session.add(obj)

    def get_by_id(self, application_id: uuid.UUID) -> Optional[ExpertApplication]:
        return self.session.get(ExpertApplication, application_id)

    def get_by_user(self, user_id: uuid.UUID) -> Optional[ExpertApplication]:
        return self.session.scalars(select(ExpertApplication).where(ExpertApplication.user_id == user_id)).first()

    def list_applications(self, status: Optional[str] = None, submitted_from: Optional[datetime] = None,
                          submitted_to: Optional[datetime] = None, descending: bool = True) -> list[ExpertApplication]:
        stmt = select(ExpertApplication)
        if status:
            stmt = stmt.where(ExpertApplication.status == status)
        if submitted_from:
            stmt = stmt.where(ExpertApplication.submitted_at >= submitted_from)
        if submitted_to:
            stmt = stmt.where(ExpertApplication.submitted_at <= submitted_to)
        column = ExpertApplication.submitted_at
        return list(self.session.scalars(stmt.order_by(column.desc() if descending else column.asc())).all())

    def count_by_status(self) -> dict:
        stmt = select(ExpertApplication.status, func.count(ExpertApplication.id)).group_by(ExpertApplication.status)
        return {status: count for status, count in self.session.execute(stmt).all()}
