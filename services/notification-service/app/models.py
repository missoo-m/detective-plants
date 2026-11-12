import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text, Uuid
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), nullable=False)
    type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="UNREAD")
    created_at = Column(DateTime, nullable=False, default=utcnow)


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    event_id = Column(String(64), primary_key=True)
    event_type = Column(String(50), nullable=False)
    processed_at = Column(DateTime, nullable=False, default=utcnow)
