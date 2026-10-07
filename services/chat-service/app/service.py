import re
from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from .models import ChatRoom, Message, ModerationLog, ModerationRule, VideoRoom, utcnow
from .repository import ChatRepository, ModerationRepository
from .schemas import ChatRoomDTO, MessageDTO, ModerationResultDTO, ModerationRuleDTO, VideoRoomDTO
from .utils import fmt_dt, parse_uuid

MAX_TEXT_LENGTH = 2000


def _room(r: ChatRoom) -> ChatRoomDTO:
    return ChatRoomDTO(id=str(r.id), request_id=str(r.request_id), client_id=str(r.client_id),
                       expert_id=str(r.expert_id), status=r.status, created_at=fmt_dt(r.created_at))


def _message(m: Message) -> MessageDTO:
    return MessageDTO(id=str(m.id), chat_room_id=str(m.chat_room_id), sender_id=str(m.sender_id), text=m.text,
                      attachment_url=m.attachment_url, is_read=bool(m.is_read), sent_at=fmt_dt(m.sent_at))


def _video(v: VideoRoom) -> VideoRoomDTO:
    return VideoRoomDTO(id=str(v.id), chat_room_id=str(v.chat_room_id), room_url=v.room_url, status=v.status,
                        recording_url=v.recording_url, created_at=fmt_dt(v.created_at),
                        finished_at=fmt_dt(v.finished_at))


def _is_participant(room: ChatRoom, user_id: str) -> bool:
    return user_id in (str(room.client_id), str(room.expert_id))


class ChatService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    @staticmethod
    def _load_room(repo: ChatRepository, chat_room_id: str) -> ChatRoom:
        room = repo.get_room(parse_uuid(chat_room_id))
        if room is None:
            raise NotFoundError(f"Чат {chat_room_id} не найден")
        return room

    @staticmethod
    def _check_access(room: ChatRoom, user_id: Optional[str]) -> None:
        if user_id is not None and not _is_participant(room, user_id):
            raise PermissionDeniedError("Чат доступен только его участникам")

    def get_chat_room(self, chat_room_id: str, viewer_id: Optional[str] = None) -> ChatRoomDTO:
        with self._session_factory() as session:
            room = self._load_room(ChatRepository(session), chat_room_id)
            self._check_access(room, viewer_id)
            return _room(room)

    def get_chat_room_by_request(self, request_id: str, viewer_id: Optional[str] = None) -> ChatRoomDTO:
        rid = parse_uuid(request_id)
        with self._session_factory() as session:
            room = ChatRepository(session).get_room_by_request(rid)
            if room is None:
                raise NotFoundError(f"Для заявки {request_id} чат не создан")
            self._check_access(room, viewer_id)
            return _room(room)

    def list_messages(self, chat_room_id: str, unread_only: bool = False, sender_id: Optional[str] = None,
                      search: Optional[str] = None, descending: bool = False,
                      limit: Optional[int] = None) -> list[MessageDTO]:
        if limit is not None and limit < 1:
            raise InvalidValueError("limit должен быть больше 0")
        rid = parse_uuid(chat_room_id)
        sid_ = parse_uuid(sender_id) if sender_id else None
        with self._session_factory() as session:
            messages = ChatRepository(session).list_messages(rid, unread_only, sid_, search, descending, limit)
            return [_message(m) for m in messages]

    def unread_count(self, chat_room_id: str, user_id: str) -> int:
        with self._session_factory() as session:
            repo = ChatRepository(session)
            room = self._load_room(repo, chat_room_id)
            self._check_access(room, user_id)
            return repo.count_unread(room.id, parse_uuid(user_id))

    def list_video_rooms(self, chat_room_id: str) -> list[VideoRoomDTO]:
        rid = parse_uuid(chat_room_id)
        with self._session_factory() as session:
            return [_video(v) for v in ChatRepository(session).list_video_rooms(rid)]

    def list_moderation_rules(self) -> list[ModerationRuleDTO]:
        with self._session_factory() as session:
            return [ModerationRuleDTO(id=str(r.id), name=r.name, pattern=r.pattern, action=r.action)
                    for r in ModerationRepository(session).list_rules()]

    def open_room(self, request_id: str, client_id: str, expert_id: str) -> ChatRoomDTO:
        rid, cid, eid = parse_uuid(request_id), parse_uuid(client_id), parse_uuid(expert_id)
        with self._session_factory() as session:
            repo = ChatRepository(session)
            room = repo.get_room_by_request(rid)
            if room is None:
                room = ChatRoom(request_id=rid, client_id=cid, expert_id=eid, status="ACTIVE")
                repo.add(room)
                session.commit()
            return _room(room)

    def moderate(self, session: Session, user_id, text: Optional[str]) -> ModerationResultDTO:
        if not text:
            return ModerationResultDTO(allowed=True)
        verdict = ModerationResultDTO(allowed=True)
        repo = ModerationRepository(session)
        for rule in repo.list_rules():
            if re.search(rule.pattern, text):
                repo.add_log(ModerationLog(user_id=user_id, rule_id=rule.id, action=rule.action))
                if rule.action == "BLOCK":
                    return ModerationResultDTO(allowed=False, action="BLOCK", rule_name=rule.name)
                verdict = ModerationResultDTO(allowed=True, action=rule.action, rule_name=rule.name)
        return verdict

    def send_message(self, chat_room_id: str, sender_id: str, text: Optional[str] = None,
                     attachment_url: Optional[str] = None) -> MessageDTO:
        text = (text or "").strip() or None
        if text is None and not attachment_url:
            raise InvalidValueError("Сообщение должно содержать текст или вложение")
        if text and len(text) > MAX_TEXT_LENGTH:
            raise InvalidValueError(f"Сообщение не должно превышать {MAX_TEXT_LENGTH} символов")
        sender = parse_uuid(sender_id)
        with self._session_factory() as session:
            repo = ChatRepository(session)
            room = self._load_room(repo, chat_room_id)
            self._check_access(room, sender_id)
            if room.status != "ACTIVE":
                raise BusinessRuleError("Чат закрыт, отправка сообщений невозможна")
            verdict = self.moderate(session, sender, text)
            if not verdict.allowed:
                session.commit()                                  
                raise BusinessRuleError(f"Сообщение заблокировано модерацией: {verdict.rule_name}")
            message = Message(chat_room_id=room.id, sender_id=sender, text=text,
                              attachment_url=attachment_url, is_read=False)
            repo.add(message)
            session.commit()
            return _message(message)

    def mark_read(self, message_id: str, reader_id: str) -> MessageDTO:
        with self._session_factory() as session:
            repo = ChatRepository(session)
            message = repo.get_message(parse_uuid(message_id))
            if message is None:
                raise NotFoundError(f"Сообщение {message_id} не найдено")
            room = repo.get_room(message.chat_room_id)
            self._check_access(room, reader_id)
            if str(message.sender_id) == reader_id:
                raise BusinessRuleError("Автор сообщения не может отметить его прочитанным")
            message.is_read = True
            session.commit()
            return _message(message)

    def create_video_room(self, chat_room_id: str, expert_id: str) -> VideoRoomDTO:
        with self._session_factory() as session:
            repo = ChatRepository(session)
            room = self._load_room(repo, chat_room_id)
            if str(room.expert_id) != expert_id:
                raise PermissionDeniedError("Создать видеокомнату может только эксперт этого чата")
            if room.status != "ACTIVE":
                raise BusinessRuleError("Чат закрыт, видеоконсультация недоступна")
            if any(v.status != "FINISHED" for v in repo.list_video_rooms(room.id)):
                raise BusinessRuleError("Предыдущая видеоконсультация ещё не завершена")
            video = VideoRoom(chat_room_id=room.id, room_url="", status="CREATED")
            repo.add(video)
            session.flush()                                      
            video.room_url = f"https://meet.example/room/{video.id}"
            session.commit()
            return _video(video)
