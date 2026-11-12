import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.events import EventConsumer, make_event
from app.handlers import build_handlers
from app.models import Base
from app.seed import seed, sid
from app.service import RecoveryService
from tests.fakes import FakeNotificationClient, FakeStorageClient, outbox


def make_factory():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed(factory)
    return factory


def send(consumer, event_type, **payload):
    return consumer.process(json.dumps(make_event(event_type, payload)))

U1, U2 = (str(sid(f"user-{i}")) for i in (1, 2))
R3 = str(sid("req-3"))


@pytest.fixture
def service():
    return RecoveryService(make_factory(), notifications=FakeNotificationClient(), storage=FakeStorageClient())


def test_diagnosis_created_starts_tracker_once(service):
    consumer = EventConsumer(service._session_factory, build_handlers(service), consumer=object())
    raw = json.dumps(make_event("DiagnosisCreated", {"request_id": R3, "client_id": U1, "expert_id": U2,
                                                     "disease_id": "d", "description": "x", "duration_days": 10}))
    assert consumer.process(raw) == "handled" and consumer.process(raw) == "duplicate"
    tracker = service.get_tracker_by_request(R3)
    assert tracker.status == "ACTIVE" and tracker.expert_id == U2
    [event] = outbox(service._session_factory, "TrackerCreated")
    assert event["payload"]["tracker_id"] == tracker.id and event["payload"]["duration_days"] == 10


def test_second_diagnosis_event_for_same_request_is_ignored(service):
    consumer = EventConsumer(service._session_factory, build_handlers(service), consumer=object())
    for _ in range(2):
        assert send(consumer, "DiagnosisCreated", request_id=R3, client_id=U1, expert_id=U2, duration_days=7) == "handled"
    assert len(outbox(service._session_factory, "TrackerCreated")) == 1


def test_treatment_update_survives_notification_outage(service):
    from app.errors import ServiceUnavailableError

    def broken(*args):
        raise ServiceUnavailableError("notification-service недоступен")
    service._notifications.send = broken
    t1 = str(sid("track-1"))
    assert service.update_treatment(t1, U2, "Увеличить дозу препарата").change_description
    assert len(outbox(service._session_factory, "TreatmentUpdated")) == 1
