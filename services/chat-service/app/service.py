from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .errors import NotFoundError
from .models import ChatRoom, Message, ModerationRule, VideoRoom
from .repository import ChatRepository, ModerationRepository
from .schemas import ChatRoomDTO, MessageDTO, ModerationRuleDTO, VideoRoomDTO
from .utils import fmt_dt, parse_uuid


def _room(r: ChatRoom) -> ChatRoomDTO:
    return ChatRoomDTO(id=str(r.id), request_id=str(r.request_id), client_id=str(r.client_id),
                       expert_id=str(r.expert_id), status=r.status, created_at=fmt_dt(r.created_at))


def _message(m: Message) -> MessageDTO:
    return MessageDTO(id=str(m.id), chat_room_id=str(m.chat_room_id), sender_id=str(m.sender_id),
                      text=m.text, attachment_url=m.attachment_url, is_read=bool(m.is_read),
                      sent_at=fmt_dt(m.sent_at))


def _video(v: VideoRoom) -> VideoRoomDTO:
    return VideoRoomDTO(id=str(v.id), chat_room_id=str(v.chat_room_id), room_url=v.room_url,
                        status=v.status, recording_url=v.recording_url,
                        created_at=fmt_dt(v.created_at), finished_at=fmt_dt(v.finished_at))


class ChatService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    def get_chat_room(self, chat_room_id: str) -> ChatRoomDTO:
        rid = parse_uuid(chat_room_id)
        with self._session_factory() as session:
            room = ChatRepository(session).get_room(rid)
            if room is None:
                raise NotFoundError(f"Чат {chat_room_id} не найден")
            return _room(room)

    def get_chat_room_by_request(self, request_id: str) -> ChatRoomDTO:
        rid = parse_uuid(request_id)
        with self._session_factory() as session:
            room = ChatRepository(session).get_room_by_request(rid)
            if room is None:
                raise NotFoundError(f"Для заявки {request_id} чат не создан")
            return _room(room)

    def list_messages(self, chat_room_id: str) -> list[MessageDTO]:
        rid = parse_uuid(chat_room_id)
        with self._session_factory() as session:
            return [_message(m) for m in ChatRepository(session).list_messages(rid)]

    def list_video_rooms(self, chat_room_id: str) -> list[VideoRoomDTO]:
        rid = parse_uuid(chat_room_id)
        with self._session_factory() as session:
            return [_video(v) for v in ChatRepository(session).list_video_rooms(rid)]

    def list_moderation_rules(self) -> list[ModerationRuleDTO]:
        with self._session_factory() as session:
            return [ModerationRuleDTO(id=str(r.id), name=r.name, pattern=r.pattern, action=r.action)
                    for r in ModerationRepository(session).list_rules()]
