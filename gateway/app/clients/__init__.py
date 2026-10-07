from ..errors import NotFoundError 
from .admin_client import MockAdminClient
from .analytics_client import MockAnalyticsClient
from .auth_client import MockAuthClient
from .base import (
    AdminClientBase, AnalyticsClientBase, AuthClientBase, ChatClientBase, ExpertClientBase,
    NotificationClientBase, PaymentClientBase, RecoveryClientBase, RequestClientBase, SatelliteClientBase,
)
from .chat_client import MockChatClient
from .expert_client import MockExpertClient
from .notification_client import MockNotificationClient
from .payment_client import MockPaymentClient
from .recovery_client import MockRecoveryClient
from .request_client import MockRequestClient
from .satellite_client import MockSatelliteClient

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


def reset_clients() -> None:
    global auth_client, request_client, expert_client, recovery_client, chat_client
    global payment_client, notification_client, analytics_client, admin_client, satellite_client
    auth_client = MockAuthClient()
    request_client = MockRequestClient()
    expert_client = MockExpertClient()
    recovery_client = MockRecoveryClient()
    chat_client = MockChatClient()
    payment_client = MockPaymentClient()
    notification_client = MockNotificationClient()
    analytics_client = MockAnalyticsClient()
    admin_client = MockAdminClient()
    satellite_client = MockSatelliteClient()


reset_clients()