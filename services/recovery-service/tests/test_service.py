from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clients import MockNotificationClient, MockRequestClient
from app.errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from app.models import Base
from app.seed import seed, sid
from app.service import RecoveryService

U1, U2, U4 = (str(sid(f"user-{i}")) for i in (1, 2, 4))
R1, R2 = str(sid("req-1")), str(sid("req-2"))
T1 = str(sid("track-1"))


@pytest.fixture
def stubs():
    return MockRequestClient(), MockNotificationClient()


@pytest.fixture
def service(stubs):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    assert seed(factory) is True
    assert seed(factory) is False
    return RecoveryService(factory, requests=stubs[0], notifications=stubs[1])


def test_reads(service):
    t = service.get_tracker_by_request(R2)
    assert t.status == "ACTIVE" and [h.record_type for h in t.history] == ["TREATMENT_UPDATE", "PHOTO"]
    assert service.get_tracker(T1).id == t.id
    assert len(service.list_trackers(expert_id=U2)) == 1 and service.list_trackers(status="COMPLETED") == []
    with pytest.raises(NotFoundError):
        service.get_tracker_by_request(R1)
    with pytest.raises(InvalidValueError):
        service.list_trackers(status="BAD")


def test_progress_aggregate(service):
    p = service.tracker_progress(T1, now=datetime(2026, 1, 23, 12, 0))     
    assert p.total_days == 14 and p.elapsed_days == 7 and p.percent == 50.0
    assert p.photos_count == 1 and p.updates_count == 1
    assert service.tracker_progress(T1, now=datetime(2026, 3, 1)).percent == 100.0
    assert service.tracker_progress(T1, now=datetime(2026, 1, 1)).percent == 0.0


def test_create_tracker(service):
    t = service.create_tracker(R1, U1, U2, duration_days=7)
    assert t.status == "ACTIVE" and t.current_stage == "START"
    with pytest.raises(BusinessRuleError):
        service.create_tracker(R1, U1, U2)                                  
    with pytest.raises(InvalidValueError):
        service.create_tracker(str(sid("req-9")), U1, U2, duration_days=0)


def test_upload_photo(service, stubs):
    h = service.upload_photo(T1, U1, "leaf.png", b"data")
    assert h.record_type == "PHOTO" and h.photo_url.endswith("leaf.png")
    assert stubs[1].sent[-1][0] == U2                                        
    with pytest.raises(PermissionDeniedError):
        service.upload_photo(T1, U4, "leaf.png", b"data")
    with pytest.raises(InvalidValueError):
        service.upload_photo(T1, U1, "leaf.gif", b"data")


def test_update_treatment(service, stubs):
    h = service.update_treatment(T1, U2, "  Увеличить периодичность обработки ", new_stage="Лечение")
    assert h.change_description == "Увеличить периодичность обработки"
    assert service.get_tracker(T1).current_stage == "Лечение" and stubs[1].sent[-1][0] == U1
    with pytest.raises(PermissionDeniedError):
        service.update_treatment(T1, U1, "Клиент не может менять лечение")
    with pytest.raises(InvalidValueError):
        service.update_treatment(T1, U2, " ")


def test_complete_tracker(service, stubs):
    with pytest.raises(PermissionDeniedError):
        service.complete_tracker(T1, U1)
    done = service.complete_tracker(T1, U2)
    assert done.status == "COMPLETED" and stubs[0].completed == [R2]       
    with pytest.raises(BusinessRuleError):
        service.complete_tracker(T1, U2)
    with pytest.raises(BusinessRuleError):
        service.upload_photo(T1, U1, "leaf.png", b"data")                      
    assert service.tracker_progress(T1).percent == 100.0
