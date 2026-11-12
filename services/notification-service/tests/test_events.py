import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.events import EventConsumer, make_event
from app.handlers import build_handlers
from app.models import Base
from app.seed import seed, sid
from app.service import NotificationService


def make_factory():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed(factory)
    return factory


def send(consumer, event_type, **payload):
    return consumer.process(json.dumps(make_event(event_type, payload)))

U1, U2 = (str(sid(f"user-{i}")) for i in (1, 2))


@pytest.fixture
def service():
    return NotificationService(make_factory())


@pytest.fixture
def consumer(service):
    return EventConsumer(service._session_factory, build_handlers(service), consumer=object())


def test_payment_completed_notifies_client_and_expert(service, consumer):
    before = {u: len(service.list_notifications(u)) for u in (U1, U2)}
    assert send(consumer, "PaymentCompleted", request_id="r", client_id=U1, expert_id=U2, amount=25.0,
                currency="BYN") == "handled"
    assert len(service.list_notifications(U1)) == before[U1] + 1
    assert service.list_notifications(U2, notification_type="PAYMENT_RECEIVED")


def test_duplicate_event_creates_one_notification(service, consumer):
    raw = json.dumps(make_event("MessageSent", {"recipient_id": U2, "text": "Привет!", "sender_id": U1}))
    assert consumer.process(raw) == "handled" and consumer.process(raw) == "duplicate"
    assert len(service.list_notifications(U2, notification_type="NEW_MESSAGE")) == 1


def test_event_with_bad_user_is_rejected(consumer):
    assert send(consumer, "RequestCreated", client_id="не-uuid") == "rejected"


def test_all_expected_events_have_handlers(consumer):
    assert "TreatmentUpdated" not in build_handlers()
    assert {"UserRegistered", "RequestCreated", "PaymentCompleted", "UserBlocked", "SatelliteAlertCreated"} <= set(build_handlers())
