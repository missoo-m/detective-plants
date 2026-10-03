import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ExpertApplication


class ApplicationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, application_id: uuid.UUID) -> Optional[ExpertApplication]:
        return self.session.get(ExpertApplication, application_id)

    def list_applications(self, status: Optional[str] = None) -> list[ExpertApplication]:
        stmt = select(ExpertApplication)
        if status:
            stmt = stmt.where(ExpertApplication.status == status)
        return list(self.session.scalars(stmt.order_by(ExpertApplication.submitted_at.desc())).all())
