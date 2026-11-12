import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Request(Base):
    __tablename__ = "requests"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(Uuid(as_uuid=True), nullable=False)
    expert_id = Column(Uuid(as_uuid=True), nullable=True)
    symptoms = Column(Text, nullable=False)
    ai_prediagnosis = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="CREATED")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    completed_at = Column(DateTime, nullable=True)

    photos = relationship("RequestPhoto", back_populates="request",
                          order_by="RequestPhoto.uploaded_at", cascade="all, delete-orphan")


class RequestPhoto(Base):
    __tablename__ = "request_photos"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(Uuid(as_uuid=True), ForeignKey("requests.id"), nullable=False)
    url = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, nullable=False, default=utcnow)

    request = relationship("Request", back_populates="photos")


class Disease(Base):
    __tablename__ = "diseases"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    symptoms = Column(Text)
    treatment = Column(Text)


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


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    event_id = Column(String(64), primary_key=True)
    event_type = Column(String(50), nullable=False)
    processed_at = Column(DateTime, nullable=False, default=utcnow)
