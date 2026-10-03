import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ChatRoom(Base):import uuid
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

    __tablename__ = "chat_rooms"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(Uuid(as_uuid=True), unique=True, nullable=False)
    client_id = Column(Uuid(as_uuid=True), nullable=False)
    expert_id = Column(Uuid(as_uuid=True), nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=utcnow)

    messages = relationship("Message", back_populates="chat_room",
                            order_by="Message.sent_at", cascade="all, delete-orphan")
    video_rooms = relationship("VideoRoom", back_populates="chat_room",
                               order_by="VideoRoom.created_at", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_room_id = Column(Uuid(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False)
    sender_id = Column(Uuid(as_uuid=True), nullable=False)
    text = Column(Text)
    attachment_url = Column(String(500))
    is_read = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=False, default=utcnow)

    chat_room = relationship("ChatRoom", back_populates="messages")


class VideoRoom(Base):
    __tablename__ = "video_rooms"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_room_id = Column(Uuid(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False)
    room_url = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="CREATED")
    recording_url = Column(String(500))
    created_at = Column(DateTime, nullable=False, default=utcnow)
    finished_at = Column(DateTime)

    chat_room = relationship("ChatRoom", back_populates="video_rooms")


class ModerationRule(Base):
    __tablename__ = "moderation_rules"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    pattern = Column(String(500), nullable=False)
    action = Column(String(50), nullable=False)

    logs = relationship("ModerationLog", back_populates="rule")


class ModerationLog(Base):
    __tablename__ = "moderation_logs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), nullable=False)
    rule_id = Column(Uuid(as_uuid=True), ForeignKey("moderation_rules.id"), nullable=False)
    action = Column(String(50), nullable=False)
    date = Column(DateTime, nullable=False, default=utcnow)

    rule = relationship("ModerationRule", back_populates="logs")
