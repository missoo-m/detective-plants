from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .errors import InvalidValueError, NotFoundError
from .models import Notification
from .repository import NotificationRepository
from .schemas import NotificationDTO
from .utils import fmt_dt, parse_uuid

NOTIFICATION_STATUSES = {"UNREAD", "READ"}


def _dto(n: Notification) -> NotificationDTO:
    return NotificationDTO(id=str(n.id), user_id=str(n.user_id), type=n.type, message=n.message,
                           status=n.status, created_at=fmt_dt(n.created_at))


class NotificationService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    def get_notification(self, notification_id: str) -> NotificationDTO:
        nid = parse_uuid(notification_id)
        with self._session_factory() as session:
            n = NotificationRepository(session).get_by_id(nid)
            if n is None:
                raise NotFoundError(f"Уведомление {notification_id} не найдено")
            return _dto(n)

    def list_notifications(self, user_id: str, status: Optional[str] = None) -> list[NotificationDTO]:
        if status is not None and status not in NOTIFICATION_STATUSES:
            raise InvalidValueError(f"Неизвестный статус уведомления: {status}")
        uid = parse_uuid(user_id)
        with self._session_factory() as session:
            return [_dto(n) for n in NotificationRepository(session).list_for_user(uid, status)]

    def count_unread(self, user_id: str) -> int:
        uid = parse_uuid(user_id)
        with self._session_factory() as session:
            return NotificationRepository(session).count_unread(uid)
