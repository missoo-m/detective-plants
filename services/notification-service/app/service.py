from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .errors import InvalidValueError, NotFoundError, PermissionDeniedError
from .models import Notification
from .repository import NotificationRepository
from .schemas import NotificationDTO, NotificationsSummaryDTO
from .utils import fmt_dt, parse_uuid

NOTIFICATION_STATUSES = {"UNREAD", "READ"}


def _dto(n: Notification) -> NotificationDTO:
    return NotificationDTO(id=str(n.id), user_id=str(n.user_id), type=n.type, message=n.message,
                           status=n.status, created_at=fmt_dt(n.created_at))


class NotificationService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    def get_notification(self, notification_id: str) -> NotificationDTO:
        with self._session_factory() as session:
            n = NotificationRepository(session).get_by_id(parse_uuid(notification_id))
            if n is None:
                raise NotFoundError(f"Уведомление {notification_id} не найдено")
            return _dto(n)

    def list_notifications(self, user_id: str, status: Optional[str] = None, notification_type: Optional[str] = None,
                           descending: bool = True, limit: Optional[int] = None,
                           offset: int = 0) -> list[NotificationDTO]:
        if status is not None and status not in NOTIFICATION_STATUSES:
            raise InvalidValueError(f"Неизвестный статус уведомления: {status}")
        if (limit is not None and limit < 1) or offset < 0:
            raise InvalidValueError("limit должен быть больше 0, offset не может быть отрицательным")
        uid = parse_uuid(user_id)
        with self._session_factory() as session:
            items = NotificationRepository(session).list_for_user(uid, status, notification_type, descending, limit, offset)
            return [_dto(n) for n in items]

    def count_unread(self, user_id: str) -> int:
        with self._session_factory() as session:
            return NotificationRepository(session).count_unread(parse_uuid(user_id))

    def notifications_summary(self, user_id: str) -> NotificationsSummaryDTO:
        uid = parse_uuid(user_id)
        with self._session_factory() as session:
            repo = NotificationRepository(session)
            by_type = repo.count_by_type(uid)
            return NotificationsSummaryDTO(total=sum(by_type.values()), unread=repo.count_unread(uid), by_type=by_type)

    def create_notification(self, user_id: str, notification_type: str, message: str) -> NotificationDTO:
        uid = parse_uuid(user_id)
        kind, text = (notification_type or "").strip(), (message or "").strip()
        if not 1 <= len(kind) <= 50:
            raise InvalidValueError("Тип уведомления должен содержать от 1 до 50 символов")
        if not 1 <= len(text) <= 1000:
            raise InvalidValueError("Текст уведомления должен содержать от 1 до 1000 символов")
        with self._session_factory() as session:
            n = Notification(user_id=uid, type=kind, message=text, status="UNREAD")
            NotificationRepository(session).add(n)
            session.commit()
            return _dto(n)

    def mark_read(self, notification_id: str, user_id: str) -> NotificationDTO:
        with self._session_factory() as session:
            n = NotificationRepository(session).get_by_id(parse_uuid(notification_id))
            if n is None:
                raise NotFoundError(f"Уведомление {notification_id} не найдено")
            if str(n.user_id) != user_id:
                raise PermissionDeniedError("Можно отмечать только свои уведомления")
            n.status = "READ"                                 
            session.commit()
            return _dto(n)

    def mark_all_read(self, user_id: str) -> int:
        uid = parse_uuid(user_id)
        with self._session_factory() as session:
            count = NotificationRepository(session).mark_all_read(uid)
            session.commit()
            return count
