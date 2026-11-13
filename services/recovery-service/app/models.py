import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RecoveryTracker(Base):
    __tablename__ = "recovery_trackers"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(Uuid(as_uuid=True), unique=True, nullable=False)
    client_id = Column(Uuid(as_uuid=True), nullable=False)
    expert_id = Column(Uuid(as_uuid=True), nullable=False)
    start_date = Column(DateTime, nullable=False, default=utcnow)
    end_date = Column(DateTime)
    status = Column(String(20), nullable=False, default="ACTIVE")
    current_stage = Column(String(100))

    history = relationship("TreatmentHistory", back_populates="tracker",
                           order_by="TreatmentHistory.date", cascade="all, delete-orphan")


class TreatmentHistory(Base):
    __tablename__ = "treatment_history"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tracker_id = Column(Uuid(as_uuid=True), ForeignKey("recovery_trackers.id"), nullable=False)
    record_type = Column(String(20), nullable=False)
    date = Column(DateTime, nullable=False, default=utcnow)
    photo_url = Column(String(500))
    change_description = Column(Text)
    author_id = Column(Uuid(as_uuid=True), nullable=False)

    tracker = relationship("RecoveryTracker", back_populates="history")


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


class DeadLetter(Base):
    __tablename__ = "dead_letters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64))
    event_type = Column(String(50))
    reason = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    replayed_at = Column(DateTime)
