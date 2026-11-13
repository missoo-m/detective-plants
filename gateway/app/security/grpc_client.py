import importlib
from typing import Optional

from .. import config
from ..grpc_support import ServiceChannel, build, message_to_dict
from .client import AuthSecurityClient
from .identity import Identity


class GrpcAuthSecurityClient(AuthSecurityClient):
    def __init__(self, target: Optional[str] = None, channel: Optional[ServiceChannel] = None):
        self._pb = importlib.import_module("..proto.auth_pb2", package=__package__)
        grpc_module = importlib.import_module("..proto.auth_pb2_grpc", package=__package__)
        self._channel = channel or ServiceChannel(target or config.SERVICE_ADDRESSES["auth"], "auth-service")
        self._stub = self._channel.stub(grpc_module.AuthServiceStub)

    def _call(self, rpc: str, request) -> dict:
        return message_to_dict(self._channel.call(getattr(self._stub, rpc), request))

    def register(self, email: str, password: str, name: str) -> dict:
        return self._call("Register", build(self._pb.RegisterRequest, email=email, password=password, name=name))

    def login(self, email: str, password: str) -> dict:
        data = self._call("Login", build(self._pb.LoginRequest, email=email, password=password))
        return {"access_token": data["token"], "token_type": data["token_type"], "expires_in": data["expires_in"],
                "session_id": data["session_id"], "user": data["user"]}

    def verify(self, token: str) -> Identity:
        data = self._call("VerifyToken", build(self._pb.VerifyTokenRequest, token=token))
        return Identity(user_id=data["user_id"], role=data["role"], session_id=data["session_id"])

    def logout(self, token: str) -> bool:
        return bool(self._call("Logout", build(self._pb.LogoutRequest, token=token))["revoked"])
