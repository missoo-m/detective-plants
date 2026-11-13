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


def test_rejected_payment_is_refunded_once(service):
    from app.events import EventConsumer
    from app.handlers import build_handlers
    tx = service.create_payment(R3, U4, "key-refund-0001")
    before = service.expert_balance(U2).earned
    consumer = EventConsumer(service._session_factory, build_handlers(service), consumer=object())
    raw = json.dumps(make_event("PaymentRejected", {"transaction_id": tx.id, "request_id": R3, "client_id": U4,
                                                   "reason": "Заявка отменена"}))
    assert consumer.process(raw) == "handled" and consumer.process(raw) == "duplicate"
    assert service.get_transaction(tx.id).status == "FAILED"
    refunds = [t for t in service.list_transactions(request_id=R3) if t.operation_type == "REFUND"]
    assert len(refunds) == 1 and refunds[0].amount == tx.amount and refunds[0].status == "SUCCESS"
    assert service.expert_balance(U2).earned == before - tx.amount
    [event] = outbox(service._session_factory, "PaymentRefunded")
    assert event["payload"]["original_transaction_id"] == tx.id and event["payload"]["client_id"] == U4


def test_refund_is_idempotent_for_different_events(service):
    tx = service.create_payment(R3, U4, "key-refund-0002")
    assert service.refund_payment(tx.id, "причина") is not None
    assert service.refund_payment(tx.id, "ещё раз") is None
    assert len(outbox(service._session_factory, "PaymentRefunded")) == 1


def test_refund_of_unknown_transaction_is_rejected(service):
    from app.errors import NotFoundError
    with pytest.raises(NotFoundError):
        service.refund_payment(str(sid("tx-404")), "нет такой")
