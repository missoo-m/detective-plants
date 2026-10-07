import copy
from typing import Optional

from ..errors import NotFoundError, PermissionDeniedError, ValidationError
from .base import NotificationClientBase
from .common import count_by, new_id, now_iso, paginate

MOCK_NOTIFICATIONS = [
    {"id": "notif-1", "user_id": "user-1", "type": "REQUEST_CREATED", "message": "Ваша заявка создана",
     "status": "UNREAD", "created_at": "2026-01-15T10:30:00Z"},
    {"id": "notif-2", "user_id": "user-1", "type": "DIAGNOSIS_READY", "message": "Диагноз готов",
     "status": "READ", "created_at": "2026-01-16T12:10:00Z"},
    {"id": "notif-3", "user_id": "user-2", "type": "PAYMENT_RECEIVED", "message": "Оплата получена",
     "status": "UNREAD", "created_at": "2026-01-16T12:05:00Z"},
]


class MockNotificationClient(NotificationClientBase):
    #Mock Notification Service

    def __init__(self):
        self.items = copy.deepcopy(MOCK_NOTIFICATIONS)

    def list_notifications(self, user_id, status=None, notification_type=None, descending=True, limit=None,
                           offset=0) -> list[dict]:
        items = [n for n in self.items if n["user_id"] == user_id]
        if status:
            items = [n for n in items if n["status"] == status]
        if notification_type:
            items = [n for n in items if n["type"] == notification_type]
        items.sort(key=lambda n: (n["created_at"], n["id"]), reverse=descending)
        return paginate(items, limit, offset)

    def notifications_summary(self, user_id: str) -> dict:
        own = [n for n in self.items if n["user_id"] == user_id]
        return {"total": len(own), "unread": sum(1 for n in own if n["status"] == "UNREAD"),
                "by_type": count_by(own, "type")}

    def create_notification(self, user_id: str, notification_type: str, message: str) -> dict:
        kind, text = (notification_type or "").strip(), (message or "").strip()
        if not 1 <= len(kind) <= 50:
            raise ValidationError("Тип уведомления должен содержать от 1 до 50 символов")
        if not 1 <= len(text) <= 1000:
            raise ValidationError("Текст уведомления должен содержать от 1 до 1000 символов")
        item = {"id": new_id("notif"), "user_id": user_id, "type": kind, "message": text,
                "status": "UNREAD", "created_at": now_iso()}
        self.items.append(item)
        return item

    def mark_read(self, notification_id: str, user_id: str) -> dict:
        item = next((n for n in self.items if n["id"] == notification_id), None)
        if item is None:
            raise NotFoundError(f"Уведомление {notification_id} не найдено")
        if item["user_id"] != user_id:
            raise PermissionDeniedError("Можно отмечать только свои уведомления")
        item["status"] = "READ"
        return item

    def mark_all_read(self, user_id: str) -> int:
        count = 0
        for n in self.items:
            if n["user_id"] == user_id and n["status"] == "UNREAD":
                n["status"] = "READ"
                count += 1
        return count
