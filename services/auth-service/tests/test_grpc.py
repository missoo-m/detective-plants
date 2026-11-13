import pytest

pytest.importorskip("grpc")
pb = pytest.importorskip("app.proto.auth_pb2")
pb_grpc = pytest.importorskip("app.proto.auth_pb2_grpc")

from app.errors import BusinessRuleError
from app.seed import sid
from tests.helpers import make_factory, serve
from types import SimpleNamespace

from app.service import AuthService

@pytest.fixture
def api():
    service = AuthService(make_factory())
    service.revoked = []
    service.session_manager = SimpleNamespace(revoke_user_sessions=lambda uid: service.revoked.append(uid) or 2,
                                              verify=lambda token: {"user_id": "u", "role": "CLIENT", "status": "ACTIVE", "session_id": "s"},
                                              logout=lambda token: True)
    with serve(service, "AuthServiceStub", pb_grpc) as (stub, channel):
        yield stub, channel, service


U1, U3 = str(sid("user-1")), str(sid("user-3"))


def test_get_user_with_profile(api):
    stub, channel, _ = api
    reply = channel.call(stub.GetUser, pb.GetUserRequest(user_id=U1), idempotent=True)
    assert reply.email == "anna@example.com" and reply.role == "CLIENT"


def test_validate_unknown_user(api):
    stub, channel, _ = api
    reply = channel.call(stub.ValidateUser, pb.ValidateUserRequest(user_id=str(sid("nobody"))))
    assert reply.valid is False and not reply.HasField("role")


def test_users_filter_and_summary(api):
    stub, channel, _ = api
    reply = channel.call(stub.GetUsers, pb.GetUsersRequest(role="EXPERT", sort_by="name"))
    assert reply.users and all(u.role == "EXPERT" for u in reply.users)
    summary = channel.call(stub.GetUsersSummary, pb.EmptyRequest())
    assert summary.total >= 1 and summary.by_role["EXPERT"] >= 1


def test_block_revokes_sessions_and_role_changes_at_once(api):
    stub, channel, service = api
    assert channel.call(stub.AssignRole, pb.AssignRoleRequest(user_id=U1, role="EXPERT")).role == "EXPERT"
    result = channel.call(stub.SetUserStatus, pb.SetUserStatusRequest(user_id=U1, status="BLOCKED"))
    assert result.user.status == "BLOCKED" and result.revoked_sessions == 2 and service.revoked == [U1]
    with pytest.raises(BusinessRuleError):
        channel.call(stub.SetUserStatus, pb.SetUserStatusRequest(user_id=U3, status="BLOCKED"))


def test_verify_token_delegates_to_session_manager(api):
    stub, channel, _ = api
    assert channel.call(stub.VerifyToken, pb.VerifyTokenRequest(token="t")).session_id == "s"
