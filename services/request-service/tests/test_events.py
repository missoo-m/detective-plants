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

    now = [0.0]
    relay = OutboxRelay(service._session_factory, Producer(), clock=lambda: now[0])
    assert relay.flush_once() == 0 and sent == []
    state["down"] = False
    assert relay.flush_once() == 0
    now[0] = 1.0
    assert relay.flush_once() == 1 and sent == [("request.events", R1, "ExpertSelected")]
    assert relay.flush_once() == 0


def test_payment_for_cancelled_request_publishes_rejection(service, consumer):
    service.cancel_request(R1, U1)
    assert send(consumer, "PaymentCompleted", request_id=R1, client_id=U1, expert_id=U2, amount=25.0,
                transaction_id="tx-1") == "handled"
    assert service.get_request(R1).status == "CANCELLED"
    [event] = outbox(service._session_factory, "PaymentRejected")
    assert event["payload"]["transaction_id"] == "tx-1" and event["payload"]["request_id"] == R1
    assert "CANCELLED" in event["payload"]["reason"]


def test_rejected_events_are_kept_in_dead_letters_and_can_be_replayed(service, consumer):
    from app.models import DeadLetter
    unknown = str(sid("req-404"))
    assert send(consumer, "PaymentCompleted", request_id=unknown) == "rejected"
    with service._session_factory() as session:
        letters = session.query(DeadLetter).all()
    assert len(letters) == 1 and "не найден" in letters[0].reason and letters[0].replayed_at is None
    assert consumer.replay_dead_letters()["still_failing"] == 1


def test_event_carries_correlation_id_of_the_scenario(service):
    from app import logging_setup
    token = logging_setup.correlation_id.set("scenario-77")
    try:
        service.select_expert(R1, U1, U2)
    finally:
        logging_setup.correlation_id.reset(token)
    assert outbox(service._session_factory, "ExpertSelected")[0]["correlation_id"] == "scenario-77"


def test_disease_directory_is_cached(service):
    from app import cache
    disease = str(sid("dis-1"))
    first = service.get_disease(disease)
    assert service.get_disease(disease) == first and cache.get_cache().stats()["hits"] == 1
    assert len(service.list_diseases()) >= 1 and service.list_diseases() == service.list_diseases()
