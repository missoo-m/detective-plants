import pytest

pytest.importorskip("grpc")
pb = pytest.importorskip("app.proto.expert_pb2")
pb_grpc = pytest.importorskip("app.proto.expert_pb2_grpc")

from app.errors import NotFoundError
from app.seed import sid
from tests.helpers import make_factory, serve
from app.service import ExpertService
from tests.fakes import FakeAuthClient, FakeRequestClient

@pytest.fixture
def api():
    service = ExpertService(make_factory(), auth=FakeAuthClient(), requests=FakeRequestClient())
    with serve(service, "ExpertServiceStub", pb_grpc) as (stub, channel):
        yield stub, channel, service


R1, R2 = str(sid("req-1")), str(sid("req-2"))
U2 = str(sid("user-2"))


def test_list_responses(api):
    stub, channel, _ = api
    reply = channel.call(stub.ListResponses, pb.ListResponsesRequest(request_id=R1), idempotent=True)
    assert [r.expert_id for r in reply.responses] == [U2]


def test_get_diagnosis_by_request_with_checklist(api):
    stub, channel, _ = api
    reply = channel.call(stub.GetDiagnosis, pb.GetDiagnosisRequest(request_id=R2))
    assert reply.request_id == R2 and len(reply.checklist) >= 2
    by_id = channel.call(stub.GetDiagnosisById, pb.GetDiagnosisByIdRequest(diagnosis_id=reply.id))
    assert by_id.id == reply.id


def test_missing_diagnosis(api):
    stub, channel, _ = api
    with pytest.raises(NotFoundError):
        channel.call(stub.GetDiagnosis, pb.GetDiagnosisRequest(request_id=R1))
