
from abc import ABC, abstractmethod
from typing import Optional


class NotFoundError(ValueError):
    pass


class AuthClientBase(ABC):
    @abstractmethod
    def get_user(self, user_id: str) -> dict: ...

    @abstractmethod
    def list_users(self, role: Optional[str] = None, status: Optional[str] = None) -> list[dict]: ...

    @abstractmethod
    def validate_user(self, user_id: str) -> dict: ...


class RequestClientBase(ABC):
    @abstractmethod
    def get_request(self, request_id: str) -> dict: ...

    @abstractmethod
    def list_requests(self, client_id: Optional[str] = None, expert_id: Optional[str] = None,
                      status: Optional[str] = None) -> list[dict]: ...

    @abstractmethod
    def list_available_requests(self) -> list[dict]: ...

    @abstractmethod
    def get_disease(self, disease_id: str) -> dict: ...


class ExpertClientBase(ABC):
    @abstractmethod
    def list_responses(self, request_id: str) -> list[dict]: ...

    @abstractmethod
    def get_diagnosis(self, diagnosis_id: str) -> dict: ...

    @abstractmethod
    def get_diagnosis_by_request(self, request_id: str) -> dict: ...


class RecoveryClientBase(ABC):
    @abstractmethod
    def get_tracker(self, tracker_id: str) -> dict: ...

    @abstractmethod
    def get_tracker_by_request(self, request_id: str) -> Optional[dict]: ...


class ChatClientBase(ABC):
    @abstractmethod
    def get_chat_room(self, chat_room_id: str) -> dict: ...

    @abstractmethod
    def get_chat_room_by_request(self, request_id: str) -> Optional[dict]: ...

    @abstractmethod
    def list_messages(self, chat_room_id: str) -> list[dict]: ...


class PaymentClientBase(ABC):
    @abstractmethod
    def get_transaction(self, transaction_id: str) -> dict: ...

    @abstractmethod
    def list_transactions(self, request_id: Optional[str] = None,
                          user_id: Optional[str] = None) -> list[dict]: ...

    @abstractmethod
    def list_withdrawals(self, expert_id: Optional[str] = None) -> list[dict]: ...


class NotificationClientBase(ABC):
    @abstractmethod
    def list_notifications(self, user_id: str, status: Optional[str] = None) -> list[dict]: ...


class AnalyticsClientBase(ABC):
    @abstractmethod
    def get_expert_stats(self, expert_id: str) -> dict: ...

    @abstractmethod
    def list_disease_stats(self, period: str) -> list[dict]: ...


class AdminClientBase(ABC):
    @abstractmethod
    def list_expert_applications(self, status: Optional[str] = None) -> list[dict]: ...


class SatelliteClientBase(ABC):
    @abstractmethod
    def list_fields(self, owner_id: str) -> list[dict]: ...

    @abstractmethod
    def get_field(self, field_id: str) -> dict: ...

    @abstractmethod
    def list_measurements(self, field_id: str) -> list[dict]: ...

    @abstractmethod
    def list_alerts(self, field_id: Optional[str] = None) -> list[dict]: ...
