from abc import ABC, abstractmethod
from typing import Optional

from . import config
from .grpc_support import ServiceChannel, message_to_dict


class AuthClient(ABC):
    @abstractmethod
    def get_user(self, user_id: str) -> dict:
        pass


class ExpertClient(ABC):
    @abstractmethod
    def has_responded(self, request_id: str, expert_id: str) -> bool: ...


class AiClient(ABC):
    @abstractmethod
    def prediagnose(self, symptoms: str) -> Optional[str]: ...


class GrpcAuthClient(AuthClient):

    def __init__(self, target: Optional[str] = None, channel: Optional[ServiceChannel] = None):
        from .proto import auth_pb2 as pb, auth_pb2_grpc as pb_grpc
        self._pb = pb
        self._channel = channel or ServiceChannel(target or config.AUTH_GRPC_ADDR, "auth-service")
        self._stub = self._channel.stub(pb_grpc.AuthServiceStub)

    def get_user(self, user_id: str) -> dict:
        reply = self._channel.call(self._stub.GetUser, self._pb.GetUserRequest(user_id=user_id), idempotent=True)
        data = message_to_dict(reply)
        return {"id": data["id"], "role": data["role"], "status": data["status"]}


class GrpcExpertClient(ExpertClient):

    def __init__(self, target: Optional[str] = None, channel: Optional[ServiceChannel] = None):
        from .proto import expert_pb2 as pb, expert_pb2_grpc as pb_grpc
        self._pb = pb
        self._channel = channel or ServiceChannel(target or config.EXPERT_GRPC_ADDR, "expert-service")
        self._stub = self._channel.stub(pb_grpc.ExpertServiceStub)

    def has_responded(self, request_id: str, expert_id: str) -> bool:
        reply = self._channel.call(self._stub.ListResponses, self._pb.ListResponsesRequest(request_id=request_id),
                                   idempotent=True)
        return any(r.expert_id == expert_id for r in reply.responses)


class KeywordAiClassifier(AiClient):
    RULES = [("налёт", "Мучнистая роса"), ("гниль", "Корневая гниль"), ("пятна", "Пятнистость листьев")]

    def prediagnose(self, symptoms: str) -> Optional[str]:
        text = symptoms.lower()
        for keyword, diagnosis in self.RULES:
            if keyword in text:
                return diagnosis
        return None
