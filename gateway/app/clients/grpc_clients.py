import importlib
from typing import Optional

from .. import config
from ..cache import get_cache
from ..grpc_support import ServiceChannel, build, message_to_dict
from .base import (AdminClientBase, AnalyticsClientBase, AuthClientBase, ChatClientBase, ExpertClientBase,
                   NotificationClientBase, PaymentClientBase, RecoveryClientBase, RequestClientBase,
                   SatelliteClientBase)


class GrpcServiceClient:
    SERVICE = ""
    STUB = ""

    def __init__(self, target: Optional[str] = None, channel: Optional[ServiceChannel] = None):
        self.pb = importlib.import_module(f"..proto.{self.SERVICE}_pb2", package=__package__)
        grpc_module = importlib.import_module(f"..proto.{self.SERVICE}_pb2_grpc", package=__package__)
        self._channel = channel or ServiceChannel(target or config.SERVICE_ADDRESSES[self.SERVICE],
                                                  f"{self.SERVICE}-service")
        self._stub = self._channel.stub(getattr(grpc_module, self.STUB))

    def _call(self, rpc: str, request, read: bool = False) -> dict:
        reply = self._channel.call(getattr(self._stub, rpc), request, idempotent=read)
        return message_to_dict(reply)

    def _read(self, rpc: str, request) -> dict:
        return self._call(rpc, request, read=True)


class GrpcAuthClient(GrpcServiceClient, AuthClientBase):
    SERVICE, STUB = "auth", "AuthServiceStub"

    def get_user(self, user_id):
        return self._read("GetUser", build(self.pb.GetUserRequest, user_id=user_id))

    def list_users(self, role=None, status=None, search=None, sort_by="created_at", descending=False, limit=None,
                   offset=0):
        request = build(self.pb.GetUsersRequest, role=role, status=status, search=search, sort_by=sort_by,
                        descending=descending, limit=limit, offset=offset)
        return self._read("GetUsers", request)["users"]

    def users_summary(self):
        return self._read("GetUsersSummary", self.pb.EmptyRequest())

    def validate_user(self, user_id):
        return self._read("ValidateUser", build(self.pb.ValidateUserRequest, user_id=user_id))

    def register(self, email, password, name):
        return self._call("Register", build(self.pb.RegisterRequest, email=email, password=password, name=name))

    def login(self, email, password):
        data = self._call("Login", build(self.pb.LoginRequest, email=email, password=password))
        return {"access_token": data["token"], "token_type": data["token_type"], "expires_in": data["expires_in"],
                "session_id": data["session_id"], "user": data["user"]}

    def update_profile(self, user_id, name=None, photo_url=None, description=None, language=None):
        return self._call("UpdateProfile", build(self.pb.UpdateProfileRequest, user_id=user_id, name=name,
                                                 photo_url=photo_url, description=description, language=language))

    def assign_role(self, user_id, role):
        return self._call("AssignRole", build(self.pb.AssignRoleRequest, user_id=user_id, role=role))

    def set_status(self, user_id, status):
        return self._call("SetUserStatus", build(self.pb.SetUserStatusRequest, user_id=user_id, status=status))["user"]


class GrpcRequestClient(GrpcServiceClient, RequestClientBase):
    SERVICE, STUB = "request", "RequestServiceStub"

    def get_request(self, request_id):
        return self._read("GetRequest", build(self.pb.GetRequestRequest, request_id=request_id))

    def list_requests(self, client_id=None, expert_id=None, statuses=None, search=None, created_from=None,
                      created_to=None, has_expert=None, sort_by="created_at", descending=False, limit=None, offset=0):
        request = build(self.pb.ListRequestsRequest, client_id=client_id, expert_id=expert_id, statuses=statuses,
                        search=search, created_from=created_from, created_to=created_to, has_expert=has_expert,
                        sort_by=sort_by, descending=descending, limit=limit, offset=offset)
        return self._read("ListRequests", request)["requests"]

    def list_available_requests(self, **kwargs):
        kwargs.pop("statuses", None)
        return self._read("ListAvailableRequests", build(self.pb.ListRequestsRequest, **kwargs))["requests"]

    def requests_summary(self, client_id=None, expert_id=None):
        return self._read("GetRequestsSummary", build(self.pb.RequestsSummaryRequest, client_id=client_id,
                                                      expert_id=expert_id))

    def get_disease(self, disease_id):
        return get_cache().get_or_load(f"disease:{disease_id}", 3600, lambda: self._read(
            "GetDisease", build(self.pb.GetDiseaseRequest, disease_id=disease_id)))

    def create_request(self, client_id, symptoms, photo_urls, actor_role=None):
        return self._call("CreateRequest", build(self.pb.CreateRequestRequest, client_id=client_id, symptoms=symptoms,
                                                 photo_urls=list(photo_urls or []), actor_role=actor_role))

    def add_photo(self, request_id, client_id, file_name, content):
        return self._call("AddPhoto", build(self.pb.AddPhotoRequest, request_id=request_id, client_id=client_id,
                                            file_name=file_name or "", content=content))

    def select_expert(self, request_id, client_id, expert_id):
        return self._call("SelectExpert", build(self.pb.SelectExpertRequest, request_id=request_id,
                                                client_id=client_id, expert_id=expert_id))

    def cancel_request(self, request_id, client_id):
        return self._call("CancelRequest", build(self.pb.CancelRequestRequest, request_id=request_id,
                                                 client_id=client_id))


class GrpcExpertClient(GrpcServiceClient, ExpertClientBase):
    SERVICE, STUB = "expert", "ExpertServiceStub"

    def list_responses(self, request_id):
        return self._read("ListResponses", build(self.pb.ListResponsesRequest, request_id=request_id))["responses"]

    def responses_summary(self, expert_id):
        return self._read("GetResponsesSummary", build(self.pb.ResponsesSummaryRequest, expert_id=expert_id))

    def respond_to_request(self, request_id, expert_id, comment, actor_role=None):
        return self._call("RespondToRequest", build(self.pb.RespondToRequestRequest, request_id=request_id,
                                                    expert_id=expert_id, comment=comment, actor_role=actor_role))

    def get_diagnosis(self, diagnosis_id):
        return self._read("GetDiagnosisById", build(self.pb.GetDiagnosisByIdRequest, diagnosis_id=diagnosis_id))

    def get_diagnosis_by_request(self, request_id):
        return self._read("GetDiagnosis", build(self.pb.GetDiagnosisRequest, request_id=request_id))

    def create_diagnosis(self, request_id, expert_id, disease_id, description, duration_days, checklist,
                         actor_role=None):
        return self._call("CreateDiagnosis", build(
            self.pb.CreateDiagnosisRequest, request_id=request_id, expert_id=expert_id, disease_id=disease_id,
            description=description, duration_days=duration_days, checklist=checklist or [], actor_role=actor_role))

    def add_treatment_step(self, diagnosis_id, expert_id, step, frequency, duration_days):
        return self._call("AddTreatmentStep", build(self.pb.AddTreatmentStepRequest, diagnosis_id=diagnosis_id,
                                                    expert_id=expert_id, step=step, frequency=frequency,
                                                    duration_days=duration_days))


class GrpcRecoveryClient(GrpcServiceClient, RecoveryClientBase):
    SERVICE, STUB = "recovery", "RecoveryServiceStub"

    def get_tracker(self, tracker_id):
        return self._read("GetTracker", build(self.pb.GetTrackerRequest, tracker_id=tracker_id))

    def get_tracker_by_request(self, request_id):
        data = self._read("GetTrackerByRequest", build(self.pb.GetTrackerByRequestRequest, request_id=request_id))
        return data["tracker"] if data["found"] else None

    def tracker_progress(self, tracker_id):
        return self._read("GetTrackerProgress", build(self.pb.GetTrackerRequest, tracker_id=tracker_id))

    def upload_photo(self, tracker_id, author_id, file_name, content):
        return self._call("UploadPhoto", build(self.pb.UploadPhotoRequest, tracker_id=tracker_id, author_id=author_id,
                                               file_name=file_name or "", content=content))

    def update_treatment(self, tracker_id, expert_id, change_description, new_stage):
        return self._call("UpdateTreatment", build(self.pb.UpdateTreatmentRequest, tracker_id=tracker_id,
                                                   expert_id=expert_id, change_description=change_description,
                                                   new_stage=new_stage))

    def complete_tracker(self, tracker_id, expert_id):
        return self._call("CompleteTracker", build(self.pb.CompleteTrackerRequest, tracker_id=tracker_id,
                                                   expert_id=expert_id))


class GrpcChatClient(GrpcServiceClient, ChatClientBase):
    SERVICE, STUB = "chat", "ChatServiceStub"

    def get_chat_room(self, chat_room_id, viewer_id=None):
        return self._read("GetChatRoom", build(self.pb.GetChatRoomRequest, chat_room_id=chat_room_id,
                                               viewer_id=viewer_id))

    def get_chat_room_by_request(self, request_id, viewer_id=None):
        data = self._read("GetChatRoomByRequest", build(self.pb.GetChatRoomByRequestRequest, request_id=request_id,
                                                        viewer_id=viewer_id))
        return data["room"] if data["found"] else None

    def list_messages(self, chat_room_id, unread_only=False, sender_id=None, search=None, descending=False,
                      limit=None):
        request = build(self.pb.ListMessagesRequest, chat_room_id=chat_room_id, unread_only=unread_only,
                        sender_id=sender_id, search=search, descending=descending, limit=limit)
        return self._read("ListMessages", request)["messages"]

    def unread_count(self, chat_room_id, user_id):
        return self._read("GetUnreadCount", build(self.pb.UnreadCountRequest, chat_room_id=chat_room_id,
                                                  user_id=user_id))["count"]

    def send_message(self, chat_room_id, sender_id, text, attachment_url):
        return self._call("SendMessage", build(self.pb.SendMessageRequest, chat_room_id=chat_room_id,
                                               sender_id=sender_id, text=text, attachment_url=attachment_url))

    def mark_read(self, message_id, reader_id):
        return self._call("MarkRead", build(self.pb.MarkReadRequest, message_id=message_id, reader_id=reader_id))

    def create_video_room(self, chat_room_id, expert_id):
        return self._call("CreateVideoRoom", build(self.pb.CreateVideoRoomRequest, chat_room_id=chat_room_id,
                                                   expert_id=expert_id))


class GrpcPaymentClient(GrpcServiceClient, PaymentClientBase):
    SERVICE, STUB = "payment", "PaymentServiceStub"

    def get_transaction(self, transaction_id):
        return self._read("GetTransaction", build(self.pb.GetTransactionRequest, transaction_id=transaction_id))

    def list_transactions(self, request_id=None, user_id=None, expert_id=None, status=None, operation_type=None,
                          min_amount=None, max_amount=None, created_from=None, created_to=None, sort_by="created_at",
                          descending=False, limit=None, offset=0):
        request = build(self.pb.ListTransactionsRequest, request_id=request_id, user_id=user_id, expert_id=expert_id,
                        status=status, operation_type=operation_type, min_amount=min_amount, max_amount=max_amount,
                        created_from=created_from, created_to=created_to, sort_by=sort_by, descending=descending,
                        limit=limit, offset=offset)
        return self._read("ListTransactions", request)["transactions"]

    def transactions_summary(self, request_id=None, user_id=None, expert_id=None, status=None, operation_type=None):
        request = build(self.pb.TransactionsSummaryRequest, request_id=request_id, user_id=user_id,
                        expert_id=expert_id, status=status, operation_type=operation_type)
        return self._read("GetTransactionsSummary", request)

    def list_withdrawals(self, expert_id=None, status=None, descending=False):
        request = build(self.pb.ListWithdrawalsRequest, expert_id=expert_id, status=status, descending=descending)
        return self._read("ListWithdrawals", request)["withdrawals"]

    def expert_balance(self, expert_id):
        return self._read("GetBalance", build(self.pb.GetBalanceRequest, expert_id=expert_id))

    def create_payment(self, request_id, client_id, idempotency_key, actor_role=None):
        return self._call("CreatePayment", build(self.pb.CreatePaymentRequest, request_id=request_id,
                                                 client_id=client_id, idempotency_key=idempotency_key,
                                                 actor_role=actor_role))

    def request_withdrawal(self, expert_id, amount, actor_role=None):
        return self._call("RequestWithdrawal", build(self.pb.RequestWithdrawalRequest, expert_id=expert_id,
                                                     amount=amount, actor_role=actor_role))

    def approve_withdrawal(self, withdrawal_id, admin_id, actor_role=None):
        return self._call("ApproveWithdrawal", build(self.pb.ApproveWithdrawalRequest, withdrawal_id=withdrawal_id,
                                                     admin_id=admin_id, actor_role=actor_role))


class GrpcNotificationClient(GrpcServiceClient, NotificationClientBase):
    SERVICE, STUB = "notification", "NotificationServiceStub"

    def list_notifications(self, user_id, status=None, notification_type=None, descending=True, limit=None,
                           offset=0):
        request = build(self.pb.ListNotificationsRequest, user_id=user_id, status=status,
                        notification_type=notification_type, descending=descending, limit=limit, offset=offset)
        return self._read("ListNotifications", request)["notifications"]

    def notifications_summary(self, user_id):
        return self._read("GetNotificationsSummary", build(self.pb.NotificationsSummaryRequest, user_id=user_id))

    def mark_read(self, notification_id, user_id):
        return self._call("MarkRead", build(self.pb.MarkReadRequest, notification_id=notification_id,
                                            user_id=user_id))

    def mark_all_read(self, user_id):
        return self._call("MarkAllRead", build(self.pb.MarkAllReadRequest, user_id=user_id))["count"]


class GrpcAnalyticsClient(GrpcServiceClient, AnalyticsClientBase):
    SERVICE, STUB = "analytics", "AnalyticsServiceStub"

    def get_expert_stats(self, expert_id):
        return self._read("GetExpertStats", build(self.pb.GetExpertStatsRequest, expert_id=expert_id))

    def top_experts(self, sort_by="completed_requests", descending=True, limit=5):
        request = build(self.pb.TopExpertsRequest, sort_by=sort_by, descending=descending, limit=limit)
        return self._read("GetTopExperts", request)["experts"]

    def list_disease_stats(self, period, descending=True, limit=None):
        request = build(self.pb.DiseaseStatsRequest, period=period, descending=descending, limit=limit)
        return self._read("GetDiseaseStats", request)["items"]

    def platform_summary(self):
        return self._read("GetPlatformSummary", self.pb.EmptyRequest())


class GrpcAdminClient(GrpcServiceClient, AdminClientBase):
    SERVICE, STUB = "admin", "AdminServiceStub"

    def list_expert_applications(self, status=None, submitted_from=None, submitted_to=None, descending=True):
        request = build(self.pb.ListApplicationsRequest, status=status, submitted_from=submitted_from,
                        submitted_to=submitted_to, descending=descending)
        return self._read("ListApplications", request)["applications"]

    def applications_summary(self):
        return self._read("GetApplicationsSummary", self.pb.EmptyRequest())

    def submit_application(self, user_id, documents_url, actor_role=None):
        return self._call("SubmitApplication", build(self.pb.SubmitApplicationRequest, user_id=user_id,
                                                     documents_url=documents_url, actor_role=actor_role))

    def verify_expert(self, application_id, admin_id, approve, actor_role=None):
        return self._call("VerifyExpert", build(self.pb.VerifyExpertRequest, application_id=application_id,
                                                admin_id=admin_id, approve=approve, actor_role=actor_role))

    def block_user(self, admin_id, user_id, actor_role=None):
        return self._call("BlockUser", build(self.pb.BlockUserRequest, user_id=user_id, admin_id=admin_id,
                                             actor_role=actor_role))


class GrpcSatelliteClient(GrpcServiceClient, SatelliteClientBase):
    SERVICE, STUB = "satellite", "SatelliteServiceStub"

    def list_fields(self, owner_id):
        return self._read("ListFields", build(self.pb.ListFieldsRequest, owner_id=owner_id))["fields"]

    def get_field(self, field_id):
        return self._read("GetField", build(self.pb.GetFieldRequest, field_id=field_id))

    def list_measurements(self, field_id, descending=False, limit=None):
        request = build(self.pb.ListMeasurementsRequest, field_id=field_id, descending=descending, limit=limit)
        return self._read("ListMeasurements", request)["measurements"]

    def list_alerts(self, field_id=None, owner_id=None, alert_type=None, descending=True):
        request = build(self.pb.ListAlertsRequest, field_id=field_id, owner_id=owner_id, alert_type=alert_type,
                        descending=descending)
        return self._read("ListAlerts", request)["alerts"]

    def ndvi_summary(self, field_id):
        return self._read("GetNdviSummary", build(self.pb.GetFieldRequest, field_id=field_id))

    def create_field(self, owner_id, name, geometry):
        return self._call("CreateField", build(self.pb.CreateFieldRequest, owner_id=owner_id, name=name,
                                               geometry=geometry))
