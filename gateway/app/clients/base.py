from abc import ABC, abstractmethod
from typing import Optional

from ..errors import NotFoundError  

class AuthClientBase(ABC):
    @abstractmethod
    def get_user(self, user_id: str) -> dict: ...

    @abstractmethod
    def list_users(self, role: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None,
                   sort_by: str = "created_at", descending: bool = False, limit: Optional[int] = None,
                   offset: int = 0) -> list[dict]: ...

    @abstractmethod
    def users_summary(self) -> dict: ...

    @abstractmethod
    def validate_user(self, user_id: str) -> dict: ...

    @abstractmethod
    def register(self, email: str, password: str, name: str) -> dict: ...

    @abstractmethod
    def login(self, email: str, password: str) -> dict: ...

    @abstractmethod
    def update_profile(self, user_id: str, name: Optional[str] = None, photo_url: Optional[str] = None,
                       description: Optional[str] = None, language: Optional[str] = None) -> dict: ...

    @abstractmethod
    def assign_role(self, user_id: str, role: str) -> dict: ...

    @abstractmethod
    def set_status(self, user_id: str, status: str) -> dict: ...


class RequestClientBase(ABC):
    @abstractmethod
    def get_request(self, request_id: str) -> dict: ...

    @abstractmethod
    def list_requests(self, client_id: Optional[str] = None, expert_id: Optional[str] = None,
                      statuses: Optional[list] = None, search: Optional[str] = None,
                      created_from: Optional[str] = None, created_to: Optional[str] = None,
                      has_expert: Optional[bool] = None, sort_by: str = "created_at", descending: bool = False,
                      limit: Optional[int] = None, offset: int = 0) -> list[dict]: ...

    @abstractmethod
    def list_available_requests(self, **kwargs) -> list[dict]: ...

    @abstractmethod
    def requests_summary(self, client_id: Optional[str] = None, expert_id: Optional[str] = None) -> dict: ...

    @abstractmethod
    def get_disease(self, disease_id: str) -> dict: ...

    @abstractmethod
    def create_request(self, client_id: str, symptoms: str, photo_urls: list) -> dict: ...

    @abstractmethod
    def add_photo(self, request_id: str, client_id: str, file_name: str, content: bytes) -> dict: ...

    @abstractmethod
    def select_expert(self, request_id: str, client_id: str, expert_id: str) -> dict: ...

    @abstractmethod
    def cancel_request(self, request_id: str, client_id: str) -> dict: ...

    @abstractmethod
    def start_work(self, request_id: str) -> dict: ...

    @abstractmethod
    def complete_request(self, request_id: str) -> dict: ...


class ExpertClientBase(ABC):
    @abstractmethod
    def list_responses(self, request_id: str) -> list[dict]: ...

    @abstractmethod
    def has_responded(self, request_id: str, expert_id: str) -> bool: ...

    @abstractmethod
    def responses_summary(self, expert_id: str) -> dict: ...

    @abstractmethod
    def respond_to_request(self, request_id: str, expert_id: str, comment: Optional[str]) -> dict: ...

    @abstractmethod
    def accept_response(self, request_id: str, expert_id: str) -> None: ...

    @abstractmethod
    def get_diagnosis(self, diagnosis_id: str) -> dict: ...

    @abstractmethod
    def get_diagnosis_by_request(self, request_id: str) -> dict: ...

    @abstractmethod
    def create_diagnosis(self, request_id: str, expert_id: str, disease_id: str, description: str,
                         duration_days: int, checklist: list) -> dict: ...

    @abstractmethod
    def add_treatment_step(self, diagnosis_id: str, expert_id: str, step: str, frequency: Optional[str],
                           duration_days: Optional[int]) -> dict: ...


class RecoveryClientBase(ABC):
    @abstractmethod
    def get_tracker(self, tracker_id: str) -> dict: ...

    @abstractmethod
    def get_tracker_by_request(self, request_id: str) -> Optional[dict]: ...

    @abstractmethod
    def tracker_progress(self, tracker_id: str) -> dict: ...

    @abstractmethod
    def create_tracker(self, request_id: str, client_id: str, expert_id: str, duration_days: int) -> dict: ...

    @abstractmethod
    def upload_photo(self, tracker_id: str, author_id: str, file_name: str, content: bytes) -> dict: ...

    @abstractmethod
    def update_treatment(self, tracker_id: str, expert_id: str, change_description: str,
                         new_stage: Optional[str]) -> dict: ...

    @abstractmethod
    def complete_tracker(self, tracker_id: str, expert_id: str) -> dict: ...


class ChatClientBase(ABC):
    @abstractmethod
    def get_chat_room(self, chat_room_id: str, viewer_id: Optional[str] = None) -> dict: ...

    @abstractmethod
    def get_chat_room_by_request(self, request_id: str, viewer_id: Optional[str] = None) -> Optional[dict]: ...

    @abstractmethod
    def list_messages(self, chat_room_id: str, unread_only: bool = False, sender_id: Optional[str] = None,
                      search: Optional[str] = None, descending: bool = False,
                      limit: Optional[int] = None) -> list[dict]: ...

    @abstractmethod
    def unread_count(self, chat_room_id: str, user_id: str) -> int: ...

    @abstractmethod
    def open_room(self, request_id: str, client_id: str, expert_id: str) -> dict: ...

    @abstractmethod
    def send_message(self, chat_room_id: str, sender_id: str, text: Optional[str],
                     attachment_url: Optional[str]) -> dict: ...

    @abstractmethod
    def mark_read(self, message_id: str, reader_id: str) -> dict: ...

    @abstractmethod
    def create_video_room(self, chat_room_id: str, expert_id: str) -> dict: ...


class PaymentClientBase(ABC):
    @abstractmethod
    def get_transaction(self, transaction_id: str) -> dict: ...

    @abstractmethod
    def list_transactions(self, request_id: Optional[str] = None, user_id: Optional[str] = None,
                          expert_id: Optional[str] = None, status: Optional[str] = None,
                          operation_type: Optional[str] = None, min_amount: Optional[float] = None,
                          max_amount: Optional[float] = None, created_from: Optional[str] = None,
                          created_to: Optional[str] = None, sort_by: str = "created_at", descending: bool = False,
                          limit: Optional[int] = None, offset: int = 0) -> list[dict]: ...

    @abstractmethod
    def transactions_summary(self, request_id: Optional[str] = None, user_id: Optional[str] = None,
                             expert_id: Optional[str] = None, status: Optional[str] = None,
                             operation_type: Optional[str] = None) -> dict: ...

    @abstractmethod
    def list_withdrawals(self, expert_id: Optional[str] = None, status: Optional[str] = None,
                         descending: bool = False) -> list[dict]: ...

    @abstractmethod
    def expert_balance(self, expert_id: str) -> dict: ...

    @abstractmethod
    def create_payment(self, request_id: str, client_id: str, idempotency_key: str) -> dict: ...

    @abstractmethod
    def request_withdrawal(self, expert_id: str, amount: float) -> dict: ...

    @abstractmethod
    def approve_withdrawal(self, withdrawal_id: str, admin_id: str) -> dict: ...


class NotificationClientBase(ABC):
    @abstractmethod
    def list_notifications(self, user_id: str, status: Optional[str] = None, notification_type: Optional[str] = None,
                           descending: bool = True, limit: Optional[int] = None, offset: int = 0) -> list[dict]: ...

    @abstractmethod
    def notifications_summary(self, user_id: str) -> dict: ...

    @abstractmethod
    def create_notification(self, user_id: str, notification_type: str, message: str) -> dict: ...

    @abstractmethod
    def mark_read(self, notification_id: str, user_id: str) -> dict: ...

    @abstractmethod
    def mark_all_read(self, user_id: str) -> int: ...


class AnalyticsClientBase(ABC):
    @abstractmethod
    def get_expert_stats(self, expert_id: str) -> dict: ...

    @abstractmethod
    def top_experts(self, sort_by: str = "completed_requests", descending: bool = True,
                    limit: Optional[int] = 5) -> list[dict]: ...

    @abstractmethod
    def list_disease_stats(self, period: str, descending: bool = True, limit: Optional[int] = None) -> list[dict]: ...

    @abstractmethod
    def platform_summary(self) -> dict: ...


class AdminClientBase(ABC):
    @abstractmethod
    def list_expert_applications(self, status: Optional[str] = None, submitted_from: Optional[str] = None,
                                 submitted_to: Optional[str] = None, descending: bool = True) -> list[dict]: ...

    @abstractmethod
    def applications_summary(self) -> dict: ...

    @abstractmethod
    def submit_application(self, user_id: str, documents_url: str) -> dict: ...

    @abstractmethod
    def verify_expert(self, application_id: str, admin_id: str, approve: bool) -> dict: ...

    @abstractmethod
    def block_user(self, admin_id: str, user_id: str) -> dict: ...


class SatelliteClientBase(ABC):
    @abstractmethod
    def list_fields(self, owner_id: str) -> list[dict]: ...

    @abstractmethod
    def get_field(self, field_id: str) -> dict: ...

    @abstractmethod
    def list_measurements(self, field_id: str, descending: bool = False, limit: Optional[int] = None) -> list[dict]: ...

    @abstractmethod
    def list_alerts(self, field_id: Optional[str] = None, owner_id: Optional[str] = None,
                    alert_type: Optional[str] = None, descending: bool = True) -> list[dict]: ...

    @abstractmethod
    def ndvi_summary(self, field_id: str) -> dict: ...

    @abstractmethod
    def create_field(self, owner_id: str, name: str, geometry: str) -> dict: ...
