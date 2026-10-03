
from typing import Optional

import strawberry
from strawberry.types import Info

from . import clients
from .clients.base import NotFoundError
from .api_types import (
    ApplicationStatus, ChatRoom, Diagnosis, DiseaseStats, ExpertApplication, ExpertStats,
    Notification, NotificationStatus, RecoveryTracker, Request, RequestStatus, Role,
    SatelliteAlert, SatelliteField, Transaction, User, UserStatus, Withdrawal,
    to_application, to_chat_room, to_diagnosis, to_disease_stats, to_expert_stats,
    to_alert, to_field, to_notification, to_request, to_tracker, to_transaction, to_user,
    to_withdrawal,
)


def _value(enum_value) -> Optional[str]:
    return enum_value.value if enum_value is not None else None


@strawberry.type
class Query:
    # пользователи (Auth Service)
    @strawberry.field
    def me(self, info: Info) -> User:
        #Текущий пользователь
        return to_user(clients.auth_client.get_user(info.context["current_user_id"]))

    @strawberry.field
    def user(self, id: strawberry.ID) -> Optional[User]:
        try:
            return to_user(clients.auth_client.get_user(id))
        except NotFoundError:
            return None

    @strawberry.field
    def users(self, role: Optional[Role] = None, status: Optional[UserStatus] = None) -> list[User]:
        return [to_user(u) for u in clients.auth_client.list_users(_value(role), _value(status))]

    # заявки (Request Service)
    @strawberry.field
    def request(self, id: strawberry.ID) -> Optional[Request]:
        try:
            return to_request(clients.request_client.get_request(id))
        except NotFoundError:
            return None

    @strawberry.field
    def my_requests(self, info: Info, status: Optional[RequestStatus] = None) -> list[Request]:
        data = clients.request_client.list_requests(
            client_id=info.context["current_user_id"], status=_value(status))
        return [to_request(r) for r in data]

    @strawberry.field
    def available_requests(self) -> list[Request]:
        return [to_request(r) for r in clients.request_client.list_available_requests()]

    @strawberry.field
    def requests_by_expert(self, expert_id: strawberry.ID) -> list[Request]:
        return [to_request(r) for r in clients.request_client.list_requests(expert_id=expert_id)]

    # диагнозы (Expert Service)
    @strawberry.field
    def diagnosis(self, id: strawberry.ID) -> Optional[Diagnosis]:
        try:
            return to_diagnosis(clients.expert_client.get_diagnosis(id))
        except NotFoundError:
            return None

    @strawberry.field
    def diagnosis_by_request(self, request_id: strawberry.ID) -> Optional[Diagnosis]:
        try:
            return to_diagnosis(clients.expert_client.get_diagnosis_by_request(request_id))
        except NotFoundError:
            return None

    # трекеры (Recovery Service)
    @strawberry.field
    def tracker(self, id: strawberry.ID) -> Optional[RecoveryTracker]:
        try:
            return to_tracker(clients.recovery_client.get_tracker(id))
        except NotFoundError:
            return None

    @strawberry.field
    def tracker_by_request(self, request_id: strawberry.ID) -> Optional[RecoveryTracker]:
        data = clients.recovery_client.get_tracker_by_request(request_id)
        return to_tracker(data) if data else None

    # чаты (Chat Service)
    @strawberry.field
    def chat_room(self, id: strawberry.ID) -> Optional[ChatRoom]:
        try:
            return to_chat_room(clients.chat_client.get_chat_room(id))
        except NotFoundError:
            return None

    @strawberry.field
    def chat_room_by_request(self, request_id: strawberry.ID) -> Optional[ChatRoom]:
        data = clients.chat_client.get_chat_room_by_request(request_id)
        return to_chat_room(data) if data else None

    # уведомления (Notification Service)
    @strawberry.field
    def notifications(self, info: Info, status: Optional[NotificationStatus] = None) -> list[Notification]:
        data = clients.notification_client.list_notifications(
            info.context["current_user_id"], _value(status))
        return [to_notification(n) for n in data]

    # финансы (Payment Service)
    @strawberry.field
    def transactions(self, request_id: Optional[strawberry.ID] = None) -> list[Transaction]:
        return [to_transaction(t) for t in clients.payment_client.list_transactions(request_id=request_id)]

    @strawberry.field
    def withdrawals(self, expert_id: Optional[strawberry.ID] = None) -> list[Withdrawal]:
        return [to_withdrawal(w) for w in clients.payment_client.list_withdrawals(expert_id=expert_id)]

    # администрирование (Admin Service)
    @strawberry.field
    def expert_applications(self, status: Optional[ApplicationStatus] = None) -> list[ExpertApplication]:
        return [to_application(a) for a in clients.admin_client.list_expert_applications(_value(status))]

    # спутниковый мониторинг (Satellite Service)???
    @strawberry.field
    def my_fields(self, info: Info) -> list[SatelliteField]:
        return [to_field(f) for f in clients.satellite_client.list_fields(info.context["current_user_id"])]

    @strawberry.field
    def satellite_field(self, id: strawberry.ID) -> Optional[SatelliteField]:
        try:
            return to_field(clients.satellite_client.get_field(id))
        except NotFoundError:
            return None

    @strawberry.field
    def satellite_alerts(self, field_id: Optional[strawberry.ID] = None) -> list[SatelliteAlert]:
        return [to_alert(a) for a in clients.satellite_client.list_alerts(field_id)]

    # аналитика (Analytics Service)
    @strawberry.field
    def expert_stats(self, expert_id: strawberry.ID) -> Optional[ExpertStats]:
        try:
            return to_expert_stats(clients.analytics_client.get_expert_stats(expert_id))
        except NotFoundError:
            return None

    @strawberry.field
    def disease_stats(self, period: str) -> list[DiseaseStats]:
        return [to_disease_stats(s) for s in clients.analytics_client.list_disease_stats(period)]


schema = strawberry.Schema(query=Query)
