import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Notification


class NotificationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, notification_id: uuid.UUID) -> Optional[Notification]:
        return self.session.get(Notification, notification_id)

    def list_for_user(self, user_id: uuid.UUID, status: Optional[str] = None) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if status:
            stmt = stmt.where(Notification.status == status)
        return list(self.session.scalars(stmt.order_by(Notification.created_at.desc())).all())

    def count_unread(self, user_id: uuid.UUID) -> int:
        stmt = (select(func.count()).select_from(Notification)
                .where(Notification.user_id == user_id, Notification.status == "UNREAD"))
        return self.session.scalar(stmt) or 0
