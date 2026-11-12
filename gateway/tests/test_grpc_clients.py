from concurrent import futures

import pytest

grpc = pytest.importorskip("grpc")
auth_pb2 = pytest.importorskip("app.proto.auth_pb2")
auth_pb2_grpc = pytest.importorskip("app.proto.auth_pb2_grpc")
request_pb2 = pytest.importorskip("app.proto.request_pb2")
request_pb2_grpc = pytest.importorskip("app.proto.request_pb2_grpc")

from app.clients.grpc_clients import GrpcAuthClient, GrpcRequestClient  
from app.errors import NotFoundError, ServiceUnavailableError  
from app.grpc_support import ServiceChannel 
from app.security.grpc_client import GrpcAuthSecurityClient 


class FakeAuth(auth_pb2_grpc.AuthServiceServicer):
    def GetUser(self, request, context):
        if request.user_id != "u1":
            context.abort(grpc.StatusCode.NOT_FOUND, "Пользователь не найден")
        return auth_pb2.UserResponse(id="u1", email="a@b.c", name="Анна", status="ACTIVE", created_at="2026-01-01",
                                     profile=auth_pb2.ProfileResponse(id="p", rating=4.5, language="ru"))

    def Login(self, request, context):
        return auth_pb2.AuthResponse(token="jwt", expires_in=1800, session_id="s1", token_type="bearer",
                                     user=auth_pb2.UserResponse(id="u1", email=request.email, name="Анна",
                                                                role="CLIENT", status="ACTIVE", created_at="t"))

    def VerifyToken(self, request, context):
        return auth_pb2.IdentityResponse(user_id="u1", role="CLIENT", status="ACTIVE", session_id="s1")

    def Logout(self, request, context):
        return auth_pb2.LogoutResponse(revoked=True)


class FakeRequests(request_pb2_grpc.RequestServiceServicer):
    last = None

    def ListRequests(self, request, context):
        FakeRequests.last = request
        return request_pb2.ListRequestsResponse(requests=[request_pb2.RequestResponse(
            id="r1", client_id=request.client_id, symptoms="s", status="CREATED", created_at="t",
            photos=[request_pb2.PhotoResponse(id="p", url="https://x/y.jpg", uploaded_at="t")])])


@pytest.fixture(scope="module")
def address():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    auth_pb2_grpc.add_AuthServiceServicer_to_server(FakeAuth(), server)
    request_pb2_grpc.add_RequestServiceServicer_to_server(FakeRequests(), server)
    port = server.add_insecure_port("localhost:0")
    server.start()
    yield f"localhost:{port}"
    server.stop(0)


def test_get_user_returns_dict_with_none_for_unset_fields(address):
    user = GrpcAuthClient(address).get_user("u1")
    assert user["email"] == "a@b.c" and user["role"] is None and user["profile"]["rating"] == 4.5
    assert user["profile"]["photo_url"] is None


def test_not_found_becomes_domain_error(address):
    with pytest.raises(NotFoundError, match="не найден"):
        GrpcAuthClient(address).get_user("zzz")


def test_security_client_maps_login_verify_logout(address):
    security = GrpcAuthSecurityClient(address)
    session = security.login("a@b.c", "x")
    assert session["access_token"] == "jwt" and session["session_id"] == "s1" and session["user"]["role"] == "CLIENT"
    identity = security.verify("jwt")
    assert (identity.user_id, identity.role, identity.session_id) == ("u1", "CLIENT", "s1")
    assert security.logout("jwt") is True


def test_request_filters_are_sent_and_lists_returned(address):
    items = GrpcRequestClient(address).list_requests(client_id="u1", statuses=["CREATED", "PENDING"],
                                                     created_from="2026-01-01", descending=True, limit=5)
    assert items[0]["photos"][0]["url"] == "https://x/y.jpg" and items[0]["expert_id"] is None
    sent = FakeRequests.last
    assert list(sent.statuses) == ["CREATED", "PENDING"] and sent.created_from == "2026-01-01"
    assert sent.descending is True and sent.limit == 5 and not sent.HasField("expert_id")


def test_unreachable_service_gives_service_unavailable():
    client = GrpcAuthClient(channel=ServiceChannel("localhost:1", "auth-service", timeout=0.3, retries=0))
    with pytest.raises(ServiceUnavailableError):
        client.get_user("u1")
