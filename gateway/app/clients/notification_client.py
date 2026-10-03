from typing import Optional
from .base import NotificationClientBase

MOCK_NOTIFICATIONS = {
    "user-1": [
        {"id": "notif-1", "user_id": "user-1", "type": "REQUEST_CREATED",
         "message": "Ваша заявка создана", "status": "UNREAD",
         "created_at": "2026-01-15T10:30:00Z"},
        {"id": "notif-2", "user_id": "user-1", "type": "DIAGNOSIS_READY",
         "message": "Диагноз готов", "status": "READ",
         "created_at": "2026-01-16T12:10:00Z"},
    ],
    "user-2": [
        {"id": "notif-3", "user_id": "user-2", "type": "PAYMENT_RECEIVED",
         "message": "Оплата получена", "status": "UNREAD",
         "created_at": "2026-01-16T12:05:00Z"},
    ],
}


class MockNotificationClient(NotificationClientBase):
    #Mock-клиент Notification Service

    def list_notifications(self, user_id: str,
                           status: Optional[str] = None) -> list[dict]:
        notifs = MOCK_NOTIFICATIONS.get(user_id, [])
        if status:
            notifs = [n for n in notifs if n["status"] == status]
        return notifs