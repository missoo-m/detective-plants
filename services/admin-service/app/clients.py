from abc import ABC, abstractmethod
from typing import Optional

from . import config
from .grpc_support import ServiceChannel, message_to_dict


class AuthClient(ABC):
    @abstractmethod
    def get_user(self, user_id: str) -> dict:
        pass

    @abstractmethod
    def assign_role(self, user_id: str, role: str) -> None:
        pass

    @abstractmethod
    def set_status(self, user_id: str, status: str) -> None:
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

    def assign_role(self, user_id: str, role: str) -> None:
        self._channel.call(self._stub.AssignRole, self._pb.AssignRoleRequest(user_id=user_id, role=role),
                           idempotent=True)

    def set_status(self, user_id: str, status: str) -> None:
        self._channel.call(self._stub.SetUserStatus, self._pb.SetUserStatusRequest(user_id=user_id, status=status),
                           idempotent=True)
