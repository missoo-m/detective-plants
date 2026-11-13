import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.events import EventConsumer, make_event
from app.handlers import build_handlers
from app.models import Base
from app.seed import seed, sid
from types import SimpleNamespace

from app.service import AuthService


def make_factory():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed(factory)
    return factory


def send(consumer, event_type, **payload):
    return consumer.process(json.dumps(make_event(event_type, payload)))

U1 = str(sid("user-1"))


@pytest.fixture
def service():
    svc = AuthService(make_factory())
    svc.revoked = []
    svc.session_manager = SimpleNamespace(revoke_user_sessions=lambda uid: svc.revoked.append(uid) or 1)
    return svc


@pytest.fixture
def consumer(service):
    return EventConsumer(service._session_factory, build_handlers(service), consumer=object())


def outbox(factory, event_type):
    from app.models import OutboxEvent
    with factory() as s:
        rows = s.query(OutboxEvent).order_by(OutboxEvent.seq).all()
    return [json.loads(r.body) for r in rows if r.event_type == event_type]


def test_register_publishes_user_registered(service):
    user = service.register("new.user@example.com", "strongpass1", "Новый Пользователь")
    [event] = outbox(service._session_factory, "UserRegistered")
    assert event["payload"]["user_id"] == user.id and event["payload"]["email"] == "new.user@example.com"
    assert "password" not in json.dumps(event)


def test_expert_verified_event_assigns_role(service, consumer):
    assert send(consumer, "ExpertVerified", application_id="a", user_id=U1, admin_id="x") == "handled"
    assert service.get_user(U1).role == "EXPERT"


def test_user_blocked_event_blocks_and_revokes_sessions(service, consumer):
    assert send(consumer, "UserBlocked", user_id=U1, admin_id="x") == "handled"
    assert service.get_user(U1).status == "BLOCKED" and service.revoked == [U1]


def test_user_card_is_cached_and_reset_on_block(service):
    from app import cache
    first = service.get_user(U1)
    assert service.get_user(U1) == first and cache.get_cache().stats()["hits"] == 1
    service.update_profile(U1, name="Новое Имя")       # ← до блокировки, пока ACTIVE
    assert service.get_user(U1).name == "Новое Имя"
    service.set_status(U1, "BLOCKED")
    assert service.get_user(U1).status == "BLOCKED"
    service.assign_role(U1, "EXPERT")
    assert service.get_user(U1).role == "EXPERT"


def test_unknown_user_is_not_cached(service):
    from app.errors import NotFoundError
    for _ in range(2):
        with pytest.raises(NotFoundError):
            service.get_user(str(sid("nobody")))
