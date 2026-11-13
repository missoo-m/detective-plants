import pytest

pytest.importorskip("grpc")
pb = pytest.importorskip("app.proto.notification_pb2")
pb_grpc = pytest.importorskip("app.proto.notification_pb2_grpc")

from app.errors import InvalidValueError
from app.seed import sid
from tests.helpers import make_factory, serve
from app.service import NotificationService

@pytest.fixture
def api():
    service = NotificationService(make_factory())
    with serve(service, "NotificationServiceStub", pb_grpc) as (stub, channel):
        yield stub, channel, service


U1 = str(sid("user-1"))


def test_send_notification_as_other_service_does(api):
    stub, channel, _ = api
    sent = channel.call(stub.SendNotification, pb.SendNotificationRequest(
        user_id=U1, type="TREATMENT_UPDATED", message="Эксперт скорректировал план лечения"))
    assert sent.status == "UNREAD"
    listed = channel.call(stub.ListNotifications, pb.ListNotificationsRequest(user_id=U1, status="UNREAD", limit=1))
    assert listed.notifications[0].id == sent.id
    assert channel.call(stub.MarkAllRead, pb.MarkAllReadRequest(user_id=U1)).count >= 1


def test_invalid_input_maps_to_invalid_argument(api):
    stub, channel, _ = api
    with pytest.raises(InvalidValueError):
        channel.call(stub.ListNotifications, pb.ListNotificationsRequest(user_id=U1, status="BAD"))
