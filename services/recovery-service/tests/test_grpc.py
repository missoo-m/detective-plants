import pytest

pytest.importorskip("grpc")
pb = pytest.importorskip("app.proto.recovery_pb2")
pb_grpc = pytest.importorskip("app.proto.recovery_pb2_grpc")

from app.seed import sid
from tests.helpers import make_factory, serve
from app.service import RecoveryService
from tests.fakes import FakeNotificationClient, FakeStorageClient

@pytest.fixture
def api():
    service = RecoveryService(make_factory(), notifications=FakeNotificationClient(), storage=FakeStorageClient())
    with serve(service, "RecoveryServiceStub", pb_grpc) as (stub, channel):
        yield stub, channel, service


R2, R3 = str(sid("req-2")), str(sid("req-3"))


def test_tracker_lookup_found_and_missing(api):
    stub, channel, _ = api
    found = channel.call(stub.GetTrackerByRequest, pb.GetTrackerByRequestRequest(request_id=R2))
    assert found.found and found.tracker.request_id == R2 and len(found.tracker.history) == 2
    missing = channel.call(stub.GetTrackerByRequest, pb.GetTrackerByRequestRequest(request_id=R3))
    assert missing.found is False and not missing.HasField("tracker")


def test_upload_photo_bytes_and_progress(api):
    stub, channel, _ = api
    tracker = channel.call(stub.GetTrackerByRequest, pb.GetTrackerByRequestRequest(request_id=R2)).tracker
    history = channel.call(stub.UploadPhoto, pb.UploadPhotoRequest(
        tracker_id=tracker.id, author_id=tracker.client_id, file_name="leaf.png", content=b"\x89PNG" * 1000))
    assert history.record_type == "PHOTO" and history.photo_url.endswith("leaf.png")
    assert channel.call(stub.GetTrackerProgress, pb.GetTrackerRequest(tracker_id=tracker.id)).photos_count >= 2
