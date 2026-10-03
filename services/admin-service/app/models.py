import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Uuid
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExpertApplication(Base):
    __tablename__ = "expert_applications"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), unique=True, nullable=False)     # пользователь из Auth Service
    documents_url = Column(String(500))
    status = Column(String(20), nullable=False, default="PENDING")       
    submitted_at = Column(DateTime, nullable=False, default=utcnow)
    verified_at = Column(DateTime)
