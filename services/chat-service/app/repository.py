import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ChatRoom, Message, ModerationRule, VideoRoom


class ChatRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_room(self, room_id: uuid.UUID) -> Optional[ChatRoom]:
        return self.session.get(ChatRoom, room_id)

    def get_room_by_request(self, request_id: uuid.UUID) -> Optional[ChatRoom]:
        return self.session.scalars(select(ChatRoom).where(ChatRoom.request_id == request_id)).first()

    def list_messages(self, room_id: uuid.UUID) -> list[Message]:
        stmt = select(Message).where(Message.chat_room_id == room_id).order_by(Message.sent_at)
        return list(self.session.scalars(stmt).all())

    def list_video_rooms(self, room_id: uuid.UUID) -> list[VideoRoom]:
        stmt = select(VideoRoom).where(VideoRoom.chat_room_id == room_id).order_by(VideoRoom.created_at)
        return list(self.session.scalars(stmt).all())


class ModerationRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_rules(self) -> list[ModerationRule]:
        return list(self.session.scalars(select(ModerationRule).order_by(ModerationRule.name)).all())
