"""In-memory двойники внутренних сервисов — ТОЛЬКО для тестов GraphQL-слоя"""
from app import clients

from .admin_client import MockAdminClient
from .analytics_client import MockAnalyticsClient
from .auth_client import MockAuthClient
from .chat_client import MockChatClient
from .expert_client import MockExpertClient
from .notification_client import MockNotificationClient
from .payment_client import MockPaymentClient
from .recovery_client import MockRecoveryClient
from .request_client import MockRequestClient
from .satellite_client import MockSatelliteClient
from .security import MockAuthSecurityClient


def install_fakes() -> None:
    auth = MockAuthClient()
    clients.use(auth_client=auth, request_client=MockRequestClient(), expert_client=MockExpertClient(),
                recovery_client=MockRecoveryClient(), chat_client=MockChatClient(),
                payment_client=MockPaymentClient(), notification_client=MockNotificationClient(),
                analytics_client=MockAnalyticsClient(), admin_client=MockAdminClient(),
                satellite_client=MockSatelliteClient(),
                security_client=MockAuthSecurityClient(lambda: auth))
