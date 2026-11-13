import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExpertStats(Base):
    __tablename__ = "expert_stats"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expert_id = Column(Uuid(as_uuid=True), unique=True, nullable=False)
    total_requests = Column(Integer, default=0)
    completed_requests = Column(Integer, default=0)
    avg_rating = Column(Float, default=0)
    updated_at = Column(DateTime, nullable=False, default=utcnow)


class DiseaseStats(Base):
    __tablename__ = "disease_stats"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    disease_id = Column(Uuid(as_uuid=True), nullable=False)
    count = Column(Integer, default=0)
    period = Column(String(20), nullable=False)


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    event_id = Column(String(64), primary_key=True)
    event_type = Column(String(50), nullable=False)
    processed_at = Column(DateTime, nullable=False, default=utcnow)


class EventCounter(Base):
    __tablename__ = "event_counters"
    __table_args__ = (UniqueConstraint("event_type", "period", name="uq_event_counter"),)

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)
    period = Column(String(20), nullable=False)
    count = Column(Integer, nullable=False, default=0)
    amount = Column(Float, nullable=False, default=0)


class DeadLetter(Base):
    __tablename__ = "dead_letters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64))
    event_type = Column(String(50))
    reason = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    replayed_at = Column(DateTime)
