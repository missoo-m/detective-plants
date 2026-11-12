from abc import ABC, abstractmethod
from typing import Optional

from . import config
from .grpc_support import ServiceChannel, message_to_dict


class AuthClient(ABC):
    @abstractmethod
    def get_user(self, user_id: str) -> dict:
        pass


class RequestClient(ABC):
    @abstractmethod
    def get_request(self, request_id: str) -> dict:
        pass


class GrpcAuthClient(AuthClient):

    def __init__(self, target: Optional[str] = None, channel: Optional[ServiceChannel] = None):
        from .proto import auth_pb2 as pb, auth_pb2_grpc as pb_grpc
        self._pb = pb
        self._channel = channel or ServiceChannel(target or config.AUTH_GRPC_ADDR, "auth-service")
        self._stub = self._channel.stub(pb_grpc.AuthServiceStub)

    def get_user(self, user_id: str) -> dict:
        reply = message_to_dict(self._channel.call(self._stub.GetUser, self._pb.GetUserRequest(user_id=user_id),
                                                   idempotent=True))
        return {"id": reply["id"], "role": reply["role"], "status": reply["status"]}


class GrpcRequestClient(RequestClient):

    def __init__(self, target: Optional[str] = None, channel: Optional[ServiceChannel] = None):
        from .proto import request_pb2 as pb, request_pb2_grpc as pb_grpc
        self._pb = pb
        self._channel = channel or ServiceChannel(target or config.REQUEST_GRPC_ADDR, "request-service")
        self._stub = self._channel.stub(pb_grpc.RequestServiceStub)

    def get_request(self, request_id: str) -> dict:
        reply = message_to_dict(self._channel.call(
            self._stub.GetRequest, self._pb.GetRequestRequest(request_id=request_id), idempotent=True))
        return {k: reply[k] for k in ("id", "client_id", "expert_id", "status")}
