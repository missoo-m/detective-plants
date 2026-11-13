from ..errors import NotFoundError
from ..security.client import AuthSecurityClient
from .base import (
    AdminClientBase, AnalyticsClientBase, AuthClientBase, ChatClientBase, ExpertClientBase,
    NotificationClientBase, PaymentClientBase, RecoveryClientBase, RequestClientBase, SatelliteClientBase,
)

auth_client: AuthClientBase
request_client: RequestClientBase
expert_client: ExpertClientBase
recovery_client: RecoveryClientBase
chat_client: ChatClientBase
payment_client: PaymentClientBase
notification_client: NotificationClientBase
analytics_client: AnalyticsClientBase
admin_client: AdminClientBase
satellite_client: SatelliteClientBase
security_client: AuthSecurityClient

NAMES = ("auth_client", "request_client", "expert_client", "recovery_client", "chat_client", "payment_client",
         "notification_client", "analytics_client", "admin_client", "satellite_client", "security_client")


def use(**implementations) -> None:
    unknown = set(implementations) - set(NAMES)
    if unknown:
        raise ValueError(f"Неизвестные клиенты: {', '.join(sorted(unknown))}")
    globals().update(implementations)


def init_grpc_clients() -> None:
    from ..security.grpc_client import GrpcAuthSecurityClient
    from . import grpc_clients as g
    use(auth_client=g.GrpcAuthClient(), request_client=g.GrpcRequestClient(), expert_client=g.GrpcExpertClient(),
        recovery_client=g.GrpcRecoveryClient(), chat_client=g.GrpcChatClient(), payment_client=g.GrpcPaymentClient(),
        notification_client=g.GrpcNotificationClient(), analytics_client=g.GrpcAnalyticsClient(),
        admin_client=g.GrpcAdminClient(), satellite_client=g.GrpcSatelliteClient(),
        security_client=GrpcAuthSecurityClient())
