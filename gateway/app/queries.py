from typing import Optional

import strawberry
from strawberry.types import Info

from . import clients
from .api_types import (
    ApplicationsSummary, ChatRoom, Diagnosis, DiseaseStats, ExpertApplication, ExpertBalance, ExpertStats,
    NdviSummary, Notification, NotificationsSummary, PlatformSummary, RecoveryTracker, Request, RequestsSummary,
    ResponsesSummary, SatelliteAlert, SatelliteField, TrackerProgress, Transaction, TransactionsSummary, User,
    UsersSummary, Withdrawal,
    to_alert, to_applications_summary, to_application, to_balance, to_chat_room, to_diagnosis, to_disease_stats,
    to_expert_stats, to_field, to_ndvi_summary, to_notification, to_notifications_summary, to_platform_summary,
    to_progress, to_request, to_requests_summary, to_responses_summary, to_tracker, to_transaction,
    to_transactions_summary, to_user, to_users_summary, to_withdrawal,
)
from .errors import NotFoundError
from .inputs import (
    ApplicationFilterInput, ExpertSortField, NotificationFilterInput, RequestFilterInput, RequestSortInput,
    SortDirection, TransactionFilterInput, TransactionSortInput, UserFilterInput, UserSortInput,
)
from .security.access import (
    assert_case_access, assert_owner_or_admin, assert_request_access, assert_self_or_admin, expert_scope,
    identity_of, scoped_filters,
)
from .security.identity import CLIENT, EXPERT
from .security.permissions import access


def _field(operation: str):
    return strawberry.field(permission_classes=[access(operation)])


def _desc(direction: Optional[SortDirection]) -> bool:
    return direction == SortDirection.DESC


def _request_params(flt: Optional[RequestFilterInput], sort: Optional[RequestSortInput]) -> dict:
    params: dict = {}
    if flt:
        params.update(statuses=[s.value for s in flt.statuses] if flt.statuses else None, search=flt.search,
                      created_from=flt.created_from, created_to=flt.created_to, has_expert=flt.has_expert)
    if sort:
        params.update(sort_by=sort.field.value, descending=_desc(sort.direction))
    return params


def _transaction_params(flt: Optional[TransactionFilterInput]) -> dict:
    if not flt:
        return {}
    return dict(request_id=flt.request_id, user_id=flt.user_id, expert_id=flt.expert_id, status=flt.status,
                operation_type=flt.operation_type, min_amount=flt.min_amount, max_amount=flt.max_amount,
                created_from=flt.created_from, created_to=flt.created_to)


def _scope_transactions(info: Info, params: dict) -> dict:
    identity = identity_of(info)
    if identity.role == CLIENT:
        scoped_filters(identity, client_id=params.get("user_id"))          
        params.update(user_id=identity.user_id, expert_id=None)
    elif identity.role == EXPERT:
        scoped_filters(identity, expert_id=params.get("expert_id"))
        params.update(expert_id=identity.user_id, user_id=None)
    return params


@strawberry.type
class Query:
    @_field("Query.me")
    def me(self, info: Info) -> User:
        return to_user(clients.auth_client.get_user(identity_of(info).user_id))

    @_field("Query.user")
    def user(self, info: Info, id: strawberry.ID) -> Optional[User]:
        assert_self_or_admin(identity_of(info), id)
        try:
            return to_user(clients.auth_client.get_user(id))
        except NotFoundError:
            return None

    @_field("Query.users")
    def users(self, filter: Optional[UserFilterInput] = None, sort: Optional[UserSortInput] = None,
              limit: Optional[int] = None, offset: int = 0) -> list[User]:
        params: dict = {}
        if filter:
            params.update(role=filter.role.value if filter.role else None,
                          status=filter.status.value if filter.status else None, search=filter.search)
        if sort:
            params.update(sort_by=sort.field.value, descending=_desc(sort.direction))
        return [to_user(u) for u in clients.auth_client.list_users(limit=limit, offset=offset, **params)]

    @_field("Query.usersSummary")
    def users_summary(self) -> UsersSummary:
        return to_users_summary(clients.auth_client.users_summary())

    @_field("Query.request")
    def request(self, info: Info, id: strawberry.ID) -> Optional[Request]:
        try:
            data = clients.request_client.get_request(id)
        except NotFoundError:
            return None
        assert_request_access(identity_of(info), data)
        return to_request(data)

    @_field("Query.myRequests")
    def my_requests(self, info: Info, filter: Optional[RequestFilterInput] = None,
                    sort: Optional[RequestSortInput] = None, limit: Optional[int] = None,
                    offset: int = 0) -> list[Request]:
        data = clients.request_client.list_requests(client_id=identity_of(info).user_id, limit=limit,
                                                    offset=offset, **_request_params(filter, sort))
        return [to_request(r) for r in data]

    @_field("Query.availableRequests")
    def available_requests(self, filter: Optional[RequestFilterInput] = None,
                           sort: Optional[RequestSortInput] = None, limit: Optional[int] = None,
                           offset: int = 0) -> list[Request]:
        params = _request_params(filter, sort)
        params.pop("statuses", None)
        return [to_request(r) for r in clients.request_client.list_available_requests(limit=limit, offset=offset, **params)]

    @_field("Query.requestsByExpert")
    def requests_by_expert(self, info: Info, expert_id: strawberry.ID, filter: Optional[RequestFilterInput] = None,
                           sort: Optional[RequestSortInput] = None, limit: Optional[int] = None,
                           offset: int = 0) -> list[Request]:
        expert_id = expert_scope(identity_of(info), expert_id)             # эксперт — только свои заявки
        data = clients.request_client.list_requests(expert_id=expert_id, limit=limit, offset=offset,
                                                    **_request_params(filter, sort))
        return [to_request(r) for r in data]

    @_field("Query.requestsSummary")
    def requests_summary(self, info: Info, client_id: Optional[strawberry.ID] = None,
                         expert_id: Optional[strawberry.ID] = None) -> RequestsSummary:
        scope = scoped_filters(identity_of(info), client_id, expert_id)
        return to_requests_summary(clients.request_client.requests_summary(scope["client_id"], scope["expert_id"]))

    @_field("Query.diagnosis")
    def diagnosis(self, info: Info, id: strawberry.ID) -> Optional[Diagnosis]:
        try:
            data = clients.expert_client.get_diagnosis(id)
        except NotFoundError:
            return None
        assert_case_access(identity_of(info), clients.request_client.get_request(data["request_id"]))
        return to_diagnosis(data)

    @_field("Query.diagnosisByRequest")
    def diagnosis_by_request(self, info: Info, request_id: strawberry.ID) -> Optional[Diagnosis]:
        try:
            request = clients.request_client.get_request(request_id)
        except NotFoundError:
            return None
        assert_case_access(identity_of(info), request)
        try:
            return to_diagnosis(clients.expert_client.get_diagnosis_by_request(request_id))
        except NotFoundError:
            return None

    @_field("Query.responsesSummary")
    def responses_summary(self, info: Info, expert_id: strawberry.ID) -> ResponsesSummary:
        expert_id = expert_scope(identity_of(info), expert_id)
        return to_responses_summary(clients.expert_client.responses_summary(expert_id))

    @_field("Query.tracker")
    def tracker(self, info: Info, id: strawberry.ID) -> Optional[RecoveryTracker]:
        try:
            data = clients.recovery_client.get_tracker(id)
        except NotFoundError:
            return None
        assert_case_access(identity_of(info), data)
        return to_tracker(data)

    @_field("Query.trackerByRequest")
    def tracker_by_request(self, info: Info, request_id: strawberry.ID) -> Optional[RecoveryTracker]:
        data = clients.recovery_client.get_tracker_by_request(request_id)
        if not data:
            return None
        assert_case_access(identity_of(info), data)
        return to_tracker(data)

    @_field("Query.trackerProgress")
    def tracker_progress(self, info: Info, tracker_id: strawberry.ID) -> TrackerProgress:
        assert_case_access(identity_of(info), clients.recovery_client.get_tracker(tracker_id))
        return to_progress(clients.recovery_client.tracker_progress(tracker_id))

    @_field("Query.chatRoom")
    def chat_room(self, info: Info, id: strawberry.ID) -> Optional[ChatRoom]:
        try:
            return to_chat_room(clients.chat_client.get_chat_room(id, identity_of(info).user_id))
        except NotFoundError:
            return None

    @_field("Query.chatRoomByRequest")
    def chat_room_by_request(self, info: Info, request_id: strawberry.ID) -> Optional[ChatRoom]:
        data = clients.chat_client.get_chat_room_by_request(request_id, identity_of(info).user_id)
        return to_chat_room(data) if data else None

    @_field("Query.chatUnreadCount")
    def chat_unread_count(self, info: Info, chat_room_id: strawberry.ID) -> int:
        return clients.chat_client.unread_count(chat_room_id, identity_of(info).user_id)

    @_field("Query.notifications")
    def notifications(self, info: Info, filter: Optional[NotificationFilterInput] = None, newest_first: bool = True,
                      limit: Optional[int] = None, offset: int = 0) -> list[Notification]:
        data = clients.notification_client.list_notifications(
            identity_of(info).user_id, status=filter.status.value if filter and filter.status else None,
            notification_type=filter.type if filter else None, descending=newest_first, limit=limit, offset=offset)
        return [to_notification(n) for n in data]

    @_field("Query.notificationsSummary")
    def notifications_summary(self, info: Info) -> NotificationsSummary:
        return to_notifications_summary(clients.notification_client.notifications_summary(identity_of(info).user_id))

    @_field("Query.transactions")
    def transactions(self, info: Info, filter: Optional[TransactionFilterInput] = None,
                     sort: Optional[TransactionSortInput] = None, limit: Optional[int] = None,
                     offset: int = 0) -> list[Transaction]:
        params = _scope_transactions(info, _transaction_params(filter))
        if sort:
            params.update(sort_by=sort.field.value, descending=_desc(sort.direction))
        return [to_transaction(t) for t in clients.payment_client.list_transactions(limit=limit, offset=offset, **params)]

    @_field("Query.transactionsSummary")
    def transactions_summary(self, info: Info, filter: Optional[TransactionFilterInput] = None) -> TransactionsSummary:
        params = _scope_transactions(info, _transaction_params(filter))
        for key in ("min_amount", "max_amount", "created_from", "created_to"):
            params.pop(key, None)
        return to_transactions_summary(clients.payment_client.transactions_summary(**params))

    @_field("Query.withdrawals")
    def withdrawals(self, info: Info, expert_id: Optional[strawberry.ID] = None,
                    newest_first: bool = False) -> list[Withdrawal]:
        expert_id = expert_scope(identity_of(info), expert_id)
        return [to_withdrawal(w) for w in clients.payment_client.list_withdrawals(expert_id=expert_id,
                                                                                  descending=newest_first)]

    @_field("Query.expertBalance")
    def expert_balance(self, info: Info, expert_id: strawberry.ID) -> ExpertBalance:
        """Баланс эксперта: эксперт видит только свой, администратор — любой."""
        return to_balance(clients.payment_client.expert_balance(expert_scope(identity_of(info), expert_id)))

    @_field("Query.expertApplications")
    def expert_applications(self, filter: Optional[ApplicationFilterInput] = None,
                            newest_first: bool = True) -> list[ExpertApplication]:
        data = clients.admin_client.list_expert_applications(
            status=filter.status.value if filter and filter.status else None,
            submitted_from=filter.submitted_from if filter else None,
            submitted_to=filter.submitted_to if filter else None, descending=newest_first)
        return [to_application(a) for a in data]

    @_field("Query.applicationsSummary")
    def applications_summary(self) -> ApplicationsSummary:
        return to_applications_summary(clients.admin_client.applications_summary())

    @_field("Query.expertStats")
    def expert_stats(self, info: Info, expert_id: strawberry.ID) -> Optional[ExpertStats]:
        expert_id = expert_scope(identity_of(info), expert_id)
        try:
            return to_expert_stats(clients.analytics_client.get_expert_stats(expert_id))
        except NotFoundError:
            return None

    @_field("Query.topExperts")
    def top_experts(self, sort_by: ExpertSortField = ExpertSortField.COMPLETED_REQUESTS,
                    direction: SortDirection = SortDirection.DESC, limit: int = 5) -> list[ExpertStats]:
        data = clients.analytics_client.top_experts(sort_by.value, _desc(direction), limit)
        return [to_expert_stats(s) for s in data]

    @_field("Query.diseaseStats")
    def disease_stats(self, period: str, direction: SortDirection = SortDirection.DESC,
                      limit: Optional[int] = None) -> list[DiseaseStats]:
        return [to_disease_stats(s) for s in clients.analytics_client.list_disease_stats(period, _desc(direction), limit)]

    @_field("Query.platformSummary")
    def platform_summary(self) -> PlatformSummary:
        return to_platform_summary(clients.analytics_client.platform_summary())

    @_field("Query.myFields")
    def my_fields(self, info: Info) -> list[SatelliteField]:
        return [to_field(f) for f in clients.satellite_client.list_fields(identity_of(info).user_id)]

    @_field("Query.satelliteField")
    def satellite_field(self, info: Info, id: strawberry.ID) -> Optional[SatelliteField]:
        try:
            data = clients.satellite_client.get_field(id)
        except NotFoundError:
            return None
        assert_owner_or_admin(identity_of(info), data["owner_id"])
        return to_field(data)

    @_field("Query.satelliteAlerts")
    def satellite_alerts(self, info: Info, field_id: Optional[strawberry.ID] = None,
                         alert_type: Optional[str] = None, newest_first: bool = True) -> list[SatelliteAlert]:
        identity = identity_of(info)
        owner = None
        if field_id:
            assert_owner_or_admin(identity, clients.satellite_client.get_field(field_id)["owner_id"])
        else:
            owner = identity.user_id
        data = clients.satellite_client.list_alerts(field_id=field_id, owner_id=owner, alert_type=alert_type,
                                                    descending=newest_first)
        return [to_alert(a) for a in data]

    @_field("Query.fieldNdviSummary")
    def field_ndvi_summary(self, info: Info, field_id: strawberry.ID) -> NdviSummary:
        assert_owner_or_admin(identity_of(info), clients.satellite_client.get_field(field_id)["owner_id"])
        return to_ndvi_summary(clients.satellite_client.ndvi_summary(field_id))
