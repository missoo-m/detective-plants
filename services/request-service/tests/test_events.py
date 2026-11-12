import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.events import EventConsumer, OutboxRelay, make_event
from app.handlers import build_handlers
from app.models import Base
from app.seed import seed, sid
from app.service import RequestService
from tests.fakes import FakeAuthClient, FakeExpertClient, FakeStorageClient, outbox

U1, U2 = (str(sid(f"user-{i}")) for i in (1, 2))
R1, R2 = (str(sid(f"req-{i}")) for i in (1, 2))


@pytest.fixture
def service():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed(factory)
    return RequestService(factory, auth=FakeAuthClient(), expert=FakeExpertClient(responded={(R1, U2)}),
                          storage=FakeStorageClient())


@pytest.fixture
def consumer(service):
    return EventConsumer(service._session_factory, build_handlers(service), consumer=object(), sleep=lambda s: None)


def send(consumer, event_type, **payload):
    return consumer.process(json.dumps(make_event(event_type, payload)))


def test_create_request_publishes_event(service):
    req = service.create_request(str(sid("user-4")), "Белый налёт на листьях", [])
    [event] = outbox(service._session_factory, "RequestCreated")
    assert event["payload"]["request_id"] == req.id and event["payload"]["ai_prediagnosis"] == "Мучнистая роса"
    assert event["event_type"] == "RequestCreated" and event["event_id"] and event["timestamp"].endswith("Z")


def test_payment_completed_starts_work_once(service, consumer):
    service.select_expert(R1, U1, U2)
    assert send(consumer, "PaymentCompleted", request_id=R1, client_id=U1, expert_id=U2, amount=25.0) == "handled"
    assert service.get_request(R1).status == "IN_PROGRESS"
    raw = json.dumps(make_event("PaymentCompleted", {"request_id": R1}))
    assert consumer.process(raw) == "handled" and consumer.process(raw) == "duplicate"
    assert service.get_request(R1).status == "IN_PROGRESS"


def test_payment_for_unknown_request_is_rejected(consumer):
    assert send(consumer, "PaymentCompleted", request_id=str(sid("req-404"))) == "rejected"


def test_tracker_completed_closes_request(service, consumer):
    assert send(consumer, "TrackerCompleted", request_id=R2, tracker_id="t", client_id=U1, expert_id=U2) == "handled"
    done = service.get_request(R2)
    assert done.status == "DONE" and done.completed_at is not None
    assert send(consumer, "TrackerCompleted", request_id=R2) == "handled"


def test_relay_publishes_in_order_and_survives_kafka_outage(service):
    service.select_expert(R1, U1, U2)
    sent, state = [], {"down": True}

    class Producer:
        def send(self, topic, key, body):
            if state["down"]:
                raise RuntimeError("Kafka недоступна")
            sent.append((topic, key, json.loads(body)["event_type"]))

    relay = OutboxRelay(service._session_factory, Producer())
    assert relay.flush_once() == 0 and sent == []
    state["down"] = False
    assert relay.flush_once() == 1 and sent == [("request.events", R1, "ExpertSelected")]
    assert relay.flush_once() == 0
