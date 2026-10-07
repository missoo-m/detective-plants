import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExpertResponse(Base):
    __tablename__ = "expert_responses"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(Uuid(as_uuid=True), nullable=False)   
    expert_id = Column(Uuid(as_uuid=True), nullable=False)   
    comment = Column(Text)
    status = Column(String(20), nullable=False, default="PENDING")
    created_at = Column(DateTime, nullable=False, default=utcnow)


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(Uuid(as_uuid=True), unique=True, nullable=False)
    expert_id = Column(Uuid(as_uuid=True), nullable=False)
    disease_id = Column(Uuid(as_uuid=True), nullable=False)   
    description = Column(Text)
    ai_prediagnosis = Column(Text)
    duration_days = Column(Integer, default=14)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    checklist = relationship("TreatmentChecklist", back_populates="diagnosis",
                             order_by="TreatmentChecklist.position", cascade="all, delete-orphan")


class TreatmentChecklist(Base):
    __tablename__ = "treatment_checklists"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    diagnosis_id = Column(Uuid(as_uuid=True), ForeignKey("diagnoses.id"), nullable=False)
    position = Column(Integer, nullable=False, default=0)    
    step = Column(Text, nullable=False)
    frequency = Column(String(50))
    duration_days = Column(Integer)

    diagnosis = relationship("Diagnosis", back_populates="checklist")


class MLTrainingExample(Base):
    __tablename__ = "ml_training_examples"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(Uuid(as_uuid=True), nullable=False)
    ai_prediagnosis = Column(Text)
    expert_correction = Column(Text)
    created_at = Column(DateTime, nullable=False, default=utcnow)
