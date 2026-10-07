import copy
import re
from typing import Optional

from ..errors import BusinessRuleError, NotFoundError, PermissionDeniedError, ValidationError
from .base import ChatClientBase
from .common import new_id, now_iso

MAX_TEXT_LENGTH = 2000

MOCK_CHAT_ROOMS = {
    "chat-1": {"id": "chat-1", "request_id": "req-2", "client_id": "user-1", "expert_id": "user-2",
               "status": "ACTIVE", "created_at": "2026-01-16T12:00:00Z"},
}

MOCK_MESSAGES = [
    {"id": "msg-1", "chat_room_id": "chat-1", "sender_id": "user-1",
     "text": "Здравствуйте! Посмотрите, пожалуйста, фото листьев", "attachment_url": None, "is_read": True,
     "sent_at": "2026-01-16T12:05:00Z"},
    {"id": "msg-2", "chat_room_id": "chat-1", "sender_id": "user-2",
     "text": "Добрый день! Похоже на мучнистую росу, готовлю план лечения", "attachment_url": None,
     "is_read": True, "sent_at": "2026-01-16T12:10:00Z"},
    {"id": "msg-3", "chat_room_id": "chat-1", "sender_id": "user-1", "text": "Спасибо за диагноз!",
     "attachment_url": None, "is_read": False, "sent_at": "2026-01-16T13:00:00Z"},
]

MOCK_VIDEO_ROOMS = [
    {"id": "video-1", "chat_room_id": "chat-1", "room_url": "https://meet.example/room/chat-1", "status": "FINISHED",
     "created_at": "2026-01-17T15:00:00Z"},
]

MOCK_RULES = [{"id": "rule-1", "name": "Контакты вне платформы", "pattern": r"(\+?\d[\d\s\-]{8,}\d)", "action": "WARN"}]


class MockChatClient(ChatClientBase):
    #Mock Chat Service

    def __init__(self):
        self.rooms = copy.deepcopy(MOCK_CHAT_ROOMS)
        self.messages = copy.deepcopy(MOCK_MESSAGES)
        self.video_rooms = copy.deepcopy(MOCK_VIDEO_ROOMS)
        self.rules = copy.deepcopy(MOCK_RULES)

    @staticmethod
    def _check_access(room: dict, user_id: Optional[str]) -> None:
        if user_id is not None and user_id not in (room["client_id"], room["expert_id"]):
            raise PermissionDeniedError("Чат доступен только его участникам")

    def _room(self, chat_room_id: str) -> dict:
        room = self.rooms.get(chat_room_id)
        if not room:
            raise NotFoundError(f"Чат {chat_room_id} не найден")
        return room

    # ---- чтение
    def get_chat_room(self, chat_room_id: str, viewer_id: Optional[str] = None) -> dict:
        room = self._room(chat_room_id)
        self._check_access(room, viewer_id)
        return room

    def get_chat_room_by_request(self, request_id: str, viewer_id: Optional[str] = None) -> Optional[dict]:
        room = next((r for r in self.rooms.values() if r["request_id"] == request_id), None)
        if room is not None:
            self._check_access(room, viewer_id)
        return room

    def list_messages(self, chat_room_id, unread_only=False, sender_id=None, search=None, descending=False,
                      limit=None) -> list[dict]:
        if limit is not None and limit < 1:
            raise ValidationError("limit должен быть больше 0")
        items = [m for m in self.messages if m["chat_room_id"] == chat_room_id]
        if unread_only:
            items = [m for m in items if not m["is_read"]]
        if sender_id:
            items = [m for m in items if m["sender_id"] == sender_id]
        if search:
            items = [m for m in items if m["text"] and search.lower() in m["text"].lower()]
        items.sort(key=lambda m: m["sent_at"], reverse=descending)
        return items[:limit] if limit else items

    def unread_count(self, chat_room_id: str, user_id: str) -> int:
        room = self._room(chat_room_id)
        self._check_access(room, user_id)
        return sum(1 for m in self.messages if m["chat_room_id"] == chat_room_id
                   and not m["is_read"] and m["sender_id"] != user_id)

    # ---- бизнес-операции
    def open_room(self, request_id: str, client_id: str, expert_id: str) -> dict:
        room = self.get_chat_room_by_request(request_id)
        if room is None:
            room = {"id": new_id("chat"), "request_id": request_id, "client_id": client_id,
                    "expert_id": expert_id, "status": "ACTIVE", "created_at": now_iso()}
            self.rooms[room["id"]] = room
        return room

    def send_message(self, chat_room_id: str, sender_id: str, text: Optional[str], attachment_url: Optional[str]) -> dict:
        text = (text or "").strip() or None
        if text is None and not attachment_url:
            raise ValidationError("Сообщение должно содержать текст или вложение")
        if text and len(text) > MAX_TEXT_LENGTH:
            raise ValidationError(f"Сообщение не должно превышать {MAX_TEXT_LENGTH} символов")
        room = self._room(chat_room_id)
        self._check_access(room, sender_id)
        if room["status"] != "ACTIVE":
            raise BusinessRuleError("Чат закрыт, отправка сообщений невозможна")
        for rule in self.rules:
            if text and re.search(rule["pattern"], text) and rule["action"] == "BLOCK":
                raise BusinessRuleError(f"Сообщение заблокировано модерацией: {rule['name']}")
        message = {"id": new_id("msg"), "chat_room_id": chat_room_id, "sender_id": sender_id, "text": text,
                   "attachment_url": attachment_url, "is_read": False, "sent_at": now_iso()}
        self.messages.append(message)
        return message

    def mark_read(self, message_id: str, reader_id: str) -> dict:
        message = next((m for m in self.messages if m["id"] == message_id), None)
        if message is None:
            raise NotFoundError(f"Сообщение {message_id} не найдено")
        self._check_access(self._room(message["chat_room_id"]), reader_id)
        if message["sender_id"] == reader_id:
            raise BusinessRuleError("Автор сообщения не может отметить его прочитанным")
        message["is_read"] = True
        return message

    def create_video_room(self, chat_room_id: str, expert_id: str) -> dict:
        room = self._room(chat_room_id)
        if room["expert_id"] != expert_id:
            raise PermissionDeniedError("Создать видеокомнату может только эксперт этого чата")
        if room["status"] != "ACTIVE":
            raise BusinessRuleError("Чат закрыт, видеоконсультация недоступна")
        if any(v["chat_room_id"] == chat_room_id and v["status"] != "FINISHED" for v in self.video_rooms):
            raise BusinessRuleError("Предыдущая видеоконсультация ещё не завершена")
        video_id = new_id("video")
        video = {"id": video_id, "chat_room_id": chat_room_id, "room_url": f"https://meet.example/room/{video_id}",
                 "status": "CREATED", "created_at": now_iso()}
        self.video_rooms.append(video)
        return video
