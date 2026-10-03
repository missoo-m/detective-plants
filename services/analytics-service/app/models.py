import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Uuid
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
