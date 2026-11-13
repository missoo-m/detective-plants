import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.events import EventConsumer, make_event
from app.handlers import build_handlers
from app.models import Base
from app.seed import seed, sid
from app.service import ChatService


def make_factory():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed(factory)
    return factory


def send(consumer, event_type, **payload):
    return consumer.process(json.dumps(make_event(event_type, payload)))

import json as _json

U1, U2, U4 = (str(sid(f"user-{i}")) for i in (1, 2, 4))
R2, R3 = (str(sid(f"req-{i}")) for i in (2, 3))


def outbox(factory, event_type):
    from app.models import OutboxEvent
    with factory() as s:
        rows = s.query(OutboxEvent).order_by(OutboxEvent.seq).all()
    return [_json.loads(r.body) for r in rows if r.event_type == event_type]


@pytest.fixture
def service():
    return ChatService(make_factory())


def test_payment_completed_opens_room_once(service):
    consumer = EventConsumer(service._session_factory, build_handlers(service), consumer=object())
    assert send(consumer, "PaymentCompleted", request_id=R3, client_id=U4, expert_id=U2, amount=25.0) == "handled"
    assert send(consumer, "PaymentCompleted", request_id=R3, client_id=U4, expert_id=U2, amount=25.0) == "handled"
    room = service.get_chat_room_by_request(R3)
    assert room.client_id == U4 and room.expert_id == U2 and room.status == "ACTIVE"


def test_message_sent_event_has_recipient(service):
    room = service.get_chat_room_by_request(R2)
    service.send_message(room.id, U1, "Здравствуйте, прикрепляю фото", None)
    [event] = outbox(service._session_factory, "MessageSent")
    assert event["payload"]["sender_id"] == U1 and event["payload"]["recipient_id"] == U2
    service.send_message(room.id, U2, "Добрый день", None)
    assert outbox(service._session_factory, "MessageSent")[1]["payload"]["recipient_id"] == U1
