import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import ChatRoom, Message, ModerationLog, ModerationRule, VideoRoom


class ChatRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, obj) -> None:
        self.session.add(obj)

    def get_room(self, room_id: uuid.UUID) -> Optional[ChatRoom]:
        return self.session.get(ChatRoom, room_id)

    def get_room_by_request(self, request_id: uuid.UUID) -> Optional[ChatRoom]:
        return self.session.scalars(select(ChatRoom).where(ChatRoom.request_id == request_id)).first()

    def get_message(self, message_id: uuid.UUID) -> Optional[Message]:
        return self.session.get(Message, message_id)

    def list_messages(self, room_id: uuid.UUID, unread_only: bool = False, sender_id: Optional[uuid.UUID] = None,
                      search: Optional[str] = None, descending: bool = False,
                      limit: Optional[int] = None) -> list[Message]:
        stmt = select(Message).where(Message.chat_room_id == room_id)
        if unread_only:
            stmt = stmt.where(Message.is_read.is_(False))
        if sender_id:
            stmt = stmt.where(Message.sender_id == sender_id)
        if search:
            stmt = stmt.where(Message.text.ilike(f"%{search}%"))
        stmt = stmt.order_by(Message.sent_at.desc() if descending else Message.sent_at.asc())
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).all())

    def count_unread(self, room_id: uuid.UUID, user_id: uuid.UUID) -> int:
        stmt = (select(func.count(Message.id)).where(Message.chat_room_id == room_id,
                                                     Message.is_read.is_(False), Message.sender_id != user_id))
        return self.session.scalar(stmt) or 0

    def list_video_rooms(self, room_id: uuid.UUID) -> list[VideoRoom]:
        stmt = select(VideoRoom).where(VideoRoom.chat_room_id == room_id).order_by(VideoRoom.created_at)
        return list(self.session.scalars(stmt).all())


class ModerationRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_rules(self) -> list[ModerationRule]:
        return list(self.session.scalars(select(ModerationRule).order_by(ModerationRule.name)).all())

    def add_log(self, log: ModerationLog) -> None:
        self.session.add(log)
