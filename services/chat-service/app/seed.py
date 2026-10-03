from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session_factory
from .models import ChatRoom, Message, ModerationLog, ModerationRule, VideoRoom

import uuid


def sid(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"plant-detective/{name}")


def seed(session_factory: Optional[Callable[[], Session]] = None) -> bool:
    factory = session_factory or get_session_factory()
    with factory() as session:
        if session.scalars(select(ChatRoom)).first():
            return False
        room = ChatRoom(id=sid("chat-1"), request_id=sid("req-2"), client_id=sid("user-1"),
                        expert_id=sid("user-2"), status="ACTIVE", created_at=datetime(2026, 1, 16, 12, 0))
        room.messages = [
            Message(id=sid("msg-1"), sender_id=sid("user-1"), is_read=True, sent_at=datetime(2026, 1, 16, 12, 5),
                    text="Здравствуйте! Посмотрите, пожалуйста, фото листьев"),
            Message(id=sid("msg-2"), sender_id=sid("user-2"), is_read=True, sent_at=datetime(2026, 1, 16, 12, 10),
                    text="Добрый день! Похоже на мучнистую росу, готовлю план лечения"),
            Message(id=sid("msg-3"), sender_id=sid("user-1"), is_read=False, sent_at=datetime(2026, 1, 16, 13, 0),
                    text="Спасибо за диагноз!"),
        ]
        room.video_rooms = [
            VideoRoom(id=sid("video-1"), room_url="https://meet.example/room/chat-1", status="FINISHED",
                      created_at=datetime(2026, 1, 17, 15, 0), finished_at=datetime(2026, 1, 17, 15, 20)),
        ]
        rule = ModerationRule(id=sid("rule-1"), name="Контакты вне платформы",
                              pattern=r"(\+?\d[\d\s\-]{8,}\d)", action="WARN")
        session.add_all([room, rule])
        session.flush()
        session.add(ModerationLog(id=sid("modlog-1"), user_id=sid("user-5"), rule_id=rule.id,
                                  action="WARN", date=datetime(2026, 1, 14, 9, 0)))
        session.commit()
        return True
