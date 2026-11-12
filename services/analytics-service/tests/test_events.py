import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.events import EventConsumer, make_event
from app.handlers import build_handlers
from app.models import Base
from app.seed import seed, sid
from app.service import AnalyticsService


def make_factory():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed(factory)
    return factory


def send(consumer, event_type, **payload):
    return consumer.process(json.dumps(make_event(event_type, payload)))

U2, U6 = str(sid("user-2")), str(sid("user-6"))
D1 = str(sid("dis-1"))


@pytest.fixture
def service():
    return AnalyticsService(make_factory())


@pytest.fixture
def consumer(service):
    return EventConsumer(service._session_factory, build_handlers(service), consumer=object())


def event_raw(event_type, **payload):
    return json.dumps(make_event(event_type, payload))


def test_expert_counters_follow_events(service, consumer):
    before = service.get_expert_stats(U2)
    send(consumer, "ExpertSelected", request_id="r", expert_id=U2, client_id="c")
    raw = event_raw("TrackerCompleted", request_id="r", expert_id=U2)
    assert consumer.process(raw) == "handled" and consumer.process(raw) == "duplicate"
    after = service.get_expert_stats(U2)
    assert after.total_requests == before.total_requests + 1
    assert after.completed_requests == before.completed_requests + 1      


def test_new_expert_gets_stats_row(service, consumer):
    new_expert = str(sid("user-new-expert"))
    send(consumer, "ExpertSelected", request_id="r", expert_id=new_expert, client_id="c")
    assert service.get_expert_stats(new_expert).total_requests == 1


def test_disease_and_payment_counters(service, consumer):
    send(consumer, "DiagnosisCreated", disease_id=D1, request_id="r")
    send(consumer, "PaymentCompleted", request_id="r", amount=25.0)
    send(consumer, "PaymentCompleted", request_id="r2", amount=15.0)
    counters = {(c.event_type): c for c in service.event_counters()}
    assert counters["PaymentCompleted"].count == 2 and counters["PaymentCompleted"].amount == 40.0
    assert counters["DiagnosisCreated"].count == 1
