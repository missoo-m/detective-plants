import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.events import make_event
from app.models import Base
from app.seed import seed, sid
from app.service import PaymentService
from tests.fakes import FakeAuthClient, FakeRequestClient, outbox


def make_factory():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed(factory)
    return factory


def send(consumer, event_type, **payload):
    return consumer.process(json.dumps(make_event(event_type, payload)))

U2, U3, U4 = (str(sid(f"user-{i}")) for i in (2, 3, 4))
R3 = str(sid("req-3"))


@pytest.fixture
def service():
    return PaymentService(make_factory(), auth=FakeAuthClient(), requests=FakeRequestClient())


def test_payment_completed_event_payload(service):
    tx = service.create_payment(R3, U4, "key-event-0001")
    [event] = outbox(service._session_factory, "PaymentCompleted")
    p = event["payload"]
    assert (p["transaction_id"], p["request_id"], p["client_id"], p["expert_id"]) == (tx.id, R3, U4, U2)
    assert p["amount"] == 25.0 and p["currency"] == "BYN" and event["event_type"] == "PaymentCompleted"


def test_withdrawal_events(service):
    wd = service.request_withdrawal(U2, 10.0)
    assert outbox(service._session_factory, "WithdrawalRequested")[0]["payload"]["withdrawal_id"] == wd.id
    service.approve_withdrawal(wd.id, U3)
    approved = outbox(service._session_factory, "WithdrawalApproved")[0]["payload"]
    assert approved["admin_id"] == U3 and approved["expert_id"] == U2
