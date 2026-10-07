import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.errors import InvalidValueError, NotFoundError, PermissionDeniedError
from app.models import Base
from app.seed import seed, sid
from app.service import NotificationService

U1, U2, U4 = (str(sid(f"user-{i}")) for i in (1, 2, 4))


@pytest.fixture
def service():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    assert seed(factory) is True
    assert seed(factory) is False
    return NotificationService(factory)


def test_filter_and_sort(service):
    assert [n.type for n in service.list_notifications(U1)] == ["DIAGNOSIS_READY", "REQUEST_CREATED"]   
    assert [n.type for n in service.list_notifications(U1, descending=False)][0] == "REQUEST_CREATED"
    assert [n.message for n in service.list_notifications(U1, status="UNREAD")] == ["Ваша заявка создана"]
    assert len(service.list_notifications(U1, notification_type="DIAGNOSIS_READY")) == 1
    assert len(service.list_notifications(U1, limit=1)) == 1 and service.list_notifications(U4) == []
    with pytest.raises(InvalidValueError):
        service.list_notifications(U1, status="BAD")


def test_aggregates(service):
    assert service.count_unread(U1) == 1
    s = service.notifications_summary(U1)
    assert s.total == 2 and s.unread == 1 and s.by_type == {"REQUEST_CREATED": 1, "DIAGNOSIS_READY": 1}


def test_create_notification(service):
    n = service.create_notification(U4, " TRACKER_PHOTO ", " Новое фото ")
    assert n.status == "UNREAD" and n.type == "TRACKER_PHOTO" and n.message == "Новое фото"
    assert service.count_unread(U4) == 1
    with pytest.raises(InvalidValueError):
        service.create_notification(U4, "", "Текст")
    with pytest.raises(InvalidValueError):
        service.create_notification(U4, "TYPE", " ")


def test_mark_read(service):
    unread = service.list_notifications(U1, status="UNREAD")[0]
    assert service.mark_read(unread.id, U1).status == "READ"
    assert service.mark_read(unread.id, U1).status == "READ"                
    assert service.count_unread(U1) == 0
    with pytest.raises(PermissionDeniedError):
        service.mark_read(unread.id, U2)
    with pytest.raises(NotFoundError):
        service.mark_read(str(sid("notif-999")), U1)


def test_mark_all_read(service):
    service.create_notification(U1, "A_TYPE", "Ещё одно")
    assert service.count_unread(U1) == 2
    assert service.mark_all_read(U1) == 2 and service.count_unread(U1) == 0
    assert service.mark_all_read(U1) == 0
