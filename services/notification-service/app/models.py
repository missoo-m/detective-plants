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
    status = Column(String(20), nullable=False, default="UNREAD")     # UNREAD / READ
    created_at = Column(DateTime, nullable=False, default=utcnow)
