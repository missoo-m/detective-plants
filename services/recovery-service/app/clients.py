from abc import ABC, abstractmethod
from typing import Optional

from . import config
from .grpc_support import ServiceChannel


class NotificationClient(ABC):
    @abstractmethod
    def send(self, user_id: str, notification_type: str, message: str) -> None: ...


class GrpcNotificationClient(NotificationClient):

    def __init__(self, target: Optional[str] = None, channel: Optional[ServiceChannel] = None):
        from .proto import notification_pb2 as pb, notification_pb2_grpc as pb_grpc
        self._pb = pb
        self._channel = channel or ServiceChannel(target or config.NOTIFICATION_GRPC_ADDR, "notification-service")
        self._stub = self._channel.stub(pb_grpc.NotificationServiceStub)

    def send(self, user_id: str, notification_type: str, message: str) -> None:
        self._channel.call(self._stub.SendNotification, self._pb.SendNotificationRequest(
            user_id=user_id, type=notification_type, message=message))
