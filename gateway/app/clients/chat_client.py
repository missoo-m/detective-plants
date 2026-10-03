from typing import Optional
from .base import ChatClientBase, NotFoundError

MOCK_CHAT_ROOMS = {
    "chat-1": {"id": "chat-1", "request_id": "req-2", "client_id": "user-1",
               "expert_id": "user-2", "status": "ACTIVE",
               "created_at": "2026-01-16T12:00:00Z"},
}

MOCK_MESSAGES = [
    {"id": "msg-1", "chat_room_id": "chat-1", "sender_id": "user-1",
     "text": "Здравствуйте! Посмотрите, пожалуйста, фото листьев", "attachment_url": None,
     "is_read": True, "sent_at": "2026-01-16T12:05:00Z"},
    {"id": "msg-2", "chat_room_id": "chat-1", "sender_id": "user-2",
     "text": "Добрый день! Похоже на мучнистую росу, готовлю план лечения", "attachment_url": None,
     "is_read": True, "sent_at": "2026-01-16T12:10:00Z"},
    {"id": "msg-3", "chat_room_id": "chat-1", "sender_id": "user-1",
     "text": "Спасибо за диагноз!", "attachment_url": None,
     "is_read": False, "sent_at": "2026-01-16T13:00:00Z"},
]


class MockChatClient(ChatClientBase):
    #Mock-клиент Chat Service

    def get_chat_room(self, chat_room_id: str) -> dict:
        room = MOCK_CHAT_ROOMS.get(chat_room_id)
        if not room:
            raise NotFoundError(f"Чат {chat_room_id} не найден")
        return room

    def get_chat_room_by_request(self, request_id: str) -> Optional[dict]:
        for room in MOCK_CHAT_ROOMS.values():
            if room["request_id"] == request_id:
                return room
        return None

    def list_messages(self, chat_room_id: str) -> list[dict]:
        return [m for m in MOCK_MESSAGES if m["chat_room_id"] == chat_room_id]
