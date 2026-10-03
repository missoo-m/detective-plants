import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Uuid
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
