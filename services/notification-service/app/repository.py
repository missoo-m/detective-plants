import uuid
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .models import Notification


class NotificationRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, obj) -> None:
        self.session.add(obj)

    def get_by_id(self, notification_id: uuid.UUID) -> Optional[Notification]:
        return self.session.get(Notification, notification_id)

    def list_for_user(self, user_id: uuid.UUID, status: Optional[str] = None, notification_type: Optional[str] = None,
                      descending: bool = True, limit: Optional[int] = None, offset: int = 0) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if status:
            stmt = stmt.where(Notification.status == status)
        if notification_type:
            stmt = stmt.where(Notification.type == notification_type)
        column = Notification.created_at
        stmt = stmt.order_by(column.desc() if descending else column.asc(), Notification.id)
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).all())

    def count_unread(self, user_id: uuid.UUID) -> int:
        stmt = (select(func.count(Notification.id))
                .where(Notification.user_id == user_id, Notification.status == "UNREAD"))
        return self.session.scalar(stmt) or 0

    def count_by_type(self, user_id: uuid.UUID) -> dict:
        stmt = (select(Notification.type, func.count(Notification.id))
                .where(Notification.user_id == user_id).group_by(Notification.type))
        return {kind: count for kind, count in self.session.execute(stmt).all()}

    def mark_all_read(self, user_id: uuid.UUID) -> int:
        stmt = (update(Notification).where(Notification.user_id == user_id, Notification.status == "UNREAD")
                .values(status="READ"))
        return self.session.execute(stmt).rowcount or 0
