import pytest

pytest.importorskip("grpc")
pb = pytest.importorskip("app.proto.admin_pb2")
pb_grpc = pytest.importorskip("app.proto.admin_pb2_grpc")

from app.errors import BusinessRuleError
from app.seed import sid
from tests.helpers import make_factory, serve
from app.service import AdminService
from tests.fakes import FakeAuthClient

@pytest.fixture
def api():
    service = AdminService(make_factory(), auth=FakeAuthClient())
    with serve(service, "AdminServiceStub", pb_grpc) as (stub, channel):
        yield stub, channel, service


U1, U3, U4 = (str(sid(f"user-{i}")) for i in (1, 3, 4))


def test_applications_and_verify(api):
    stub, channel, service = api
    listed = channel.call(stub.ListApplications, pb.ListApplicationsRequest(status="PENDING"))
    assert listed.applications
    verified = channel.call(stub.VerifyExpert, pb.VerifyExpertRequest(application_id=listed.applications[0].id, approve=True, admin_id=U3))
    assert verified.status == "APPROVED"
    assert channel.call(stub.GetApplicationsSummary, pb.EmptyRequest()).total >= 1


def test_block_user_and_rules(api):
    stub, channel, _ = api
    assert channel.call(stub.BlockUser, pb.BlockUserRequest(user_id=U1, admin_id=U3)).status == "BLOCKED"
    with pytest.raises(BusinessRuleError):
        channel.call(stub.BlockUser, pb.BlockUserRequest(user_id=U1, admin_id=U3))
