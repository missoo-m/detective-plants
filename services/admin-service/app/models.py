import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExpertApplication(Base):
    __tablename__ = "expert_applications"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), unique=True, nullable=False)
    documents_url = Column(String(500))
    status = Column(String(20), nullable=False, default="PENDING")
    submitted_at = Column(DateTime, nullable=False, default=utcnow)
    verified_at = Column(DateTime)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    seq = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), unique=True, nullable=False)
    topic = Column(String(100), nullable=False)
    event_key = Column(String(100))
    event_type = Column(String(50), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    published_at = Column(DateTime)
    attempts = Column(Integer, nullable=False, default=0)
