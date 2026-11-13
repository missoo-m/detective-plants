import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.events import make_event
from app.models import Base
from app.seed import seed, sid
from datetime import datetime

from app.service import SatelliteService


def make_factory():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed(factory)
    return factory


def send(consumer, event_type, **payload):
    return consumer.process(json.dumps(make_event(event_type, payload)))

U1 = str(sid("user-1"))
F2 = str(sid("fld-2"))


def outbox(factory, event_type):
    from app.models import OutboxEvent
    with factory() as s:
        rows = s.query(OutboxEvent).order_by(OutboxEvent.seq).all()
    return [json.loads(r.body) for r in rows if r.event_type == event_type]


def test_ndvi_drop_publishes_alert_event():
    service = SatelliteService(make_factory())
    service.record_measurement(F2, 0.50, datetime(2026, 1, 20, 10, 0))
    [event] = outbox(service._session_factory, "SatelliteAlertCreated")
    p = event["payload"]
    assert p["field_id"] == F2 and p["owner_id"] == U1 and p["alert_type"] == "NDVI_DROP" and "30%" in p["message"]
    service.record_measurement(F2, 0.49, datetime(2026, 1, 21, 10, 0))
    assert len(outbox(service._session_factory, "SatelliteAlertCreated")) == 1
