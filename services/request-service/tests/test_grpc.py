import pytest

pytest.importorskip("grpc")
pb = pytest.importorskip("app.proto.request_pb2")
pb_grpc = pytest.importorskip("app.proto.request_pb2_grpc")

from app.errors import AuthenticationError, NotFoundError
from app.seed import sid
from tests.helpers import make_factory, serve
from app.service import RequestService
from tests.fakes import FakeAuthClient, FakeExpertClient, FakeStorageClient

@pytest.fixture
def api():
    service = RequestService(make_factory(), auth=FakeAuthClient(), expert=FakeExpertClient(), storage=FakeStorageClient())
    with serve(service, "RequestServiceStub", pb_grpc) as (stub, channel):
        yield stub, channel, service


R1 = str(sid("req-1"))
U1 = str(sid("user-1"))


def test_get_request_over_grpc(api):
    stub, channel, _ = api
    reply = channel.call(stub.GetRequest, pb.GetRequestRequest(request_id=R1), idempotent=True)
    assert reply.id == R1 and reply.client_id == U1 and reply.status == "CREATED"
    assert not reply.HasField("expert_id") and len(reply.photos) == 2


def test_not_found_maps_to_not_found_error(api):
    stub, channel, _ = api
    with pytest.raises(NotFoundError):
        channel.call(stub.GetRequest, pb.GetRequestRequest(request_id=str(sid("req-404"))))


def test_filters_and_dates_over_grpc(api):
    stub, channel, _ = api
    request = pb.ListRequestsRequest(created_from="2026-01-16", created_to="2026-01-16", descending=True)
    request.statuses.append("IN_PROGRESS")
    reply = channel.call(stub.ListRequests, request, idempotent=True)
    assert [r.status for r in reply.requests] == ["IN_PROGRESS"]


def test_create_request_and_summary(api):
    stub, channel, _ = api
    created = channel.call(stub.CreateRequest, pb.CreateRequestRequest(
        client_id=str(sid("user-4")), symptoms="Белый налёт на листьях", photo_urls=["https://x/y.jpg"]))
    assert created.ai_prediagnosis == "Мучнистая роса"
    summary = channel.call(stub.GetRequestsSummary, pb.RequestsSummaryRequest(client_id=str(sid("user-4"))))
    assert summary.total >= 1 and summary.by_status["CREATED"] >= 1


def test_wrong_api_key_is_rejected(api):
    import grpc
    from app.grpc_support import ServiceChannel
    stub, channel, _ = api
    stranger = ServiceChannel(channel.target, "stranger", api_key="wrong", retries=0)
    with pytest.raises(AuthenticationError):
        stranger.call(stranger.stub(pb_grpc.RequestServiceStub).GetRequest, pb.GetRequestRequest(request_id=R1))
    stranger.close()
