import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(Uuid(as_uuid=True), nullable=False)
    user_id = Column(Uuid(as_uuid=True), nullable=False)
    expert_id = Column(Uuid(as_uuid=True), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    operation_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    idempotency_key = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expert_id = Column(Uuid(as_uuid=True), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    processed_at = Column(DateTime)


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
