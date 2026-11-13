import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.events import EventConsumer, make_event
from app.handlers import build_handlers
from app.models import Base
from app.seed import seed, sid
from app.service import ExpertService
from tests.fakes import FakeAuthClient, FakeRequestClient, outbox


def make_factory():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed(factory)
    return factory


def send(consumer, event_type, **payload):
    return consumer.process(json.dumps(make_event(event_type, payload)))

U1, U2, U4 = (str(sid(f"user-{i}")) for i in (1, 2, 4))
R1, R3 = (str(sid(f"req-{i}")) for i in (1, 3))


@pytest.fixture
def service():
    return ExpertService(make_factory(), auth=FakeAuthClient(), requests=FakeRequestClient())


def test_response_publishes_event_with_client(service):
    resp = service.respond_to_request(R3, U2, "Могу помочь")
    [event] = outbox(service._session_factory, "ExpertResponseCreated")
    assert event["payload"]["response_id"] == resp.id and event["payload"]["client_id"] == U4


def test_expert_selected_accepts_one_and_rejects_others(service):
    consumer = EventConsumer(service._session_factory, build_handlers(service), consumer=object())
    service.respond_to_request(R3, U2, "Первый")
    assert send(consumer, "ExpertSelected", request_id=R3, client_id=U4, expert_id=U2) == "handled"
    assert [r.status for r in service.list_responses(R3) if r.expert_id == U2] == ["ACCEPTED"]


def test_expert_selected_without_response_is_rejected(service):
    consumer = EventConsumer(service._session_factory, build_handlers(service), consumer=object())
    assert send(consumer, "ExpertSelected", request_id=R3, client_id=U4, expert_id=U2) == "rejected"
