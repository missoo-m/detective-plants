#Input-типы GraphQL
from enum import Enum
from typing import Optional

import strawberry

from .api_types import (
    ApplicationStatus, NotificationStatus, RequestStatus, Role, UserStatus,
)

#  сортировка
@strawberry.enum
class SortDirection(Enum):
    ASC = "ASC"
    DESC = "DESC"


@strawberry.enum
class RequestSortField(Enum):
    CREATED_AT = "created_at"
    STATUS = "status"


@strawberry.enum
class UserSortField(Enum):
    CREATED_AT = "created_at"
    NAME = "name"
    EMAIL = "email"


@strawberry.enum
class TransactionSortField(Enum):
    CREATED_AT = "created_at"
    AMOUNT = "amount"


@strawberry.enum
class ExpertSortField(Enum):
    TOTAL_REQUESTS = "total_requests"
    COMPLETED_REQUESTS = "completed_requests"
    AVG_RATING = "avg_rating"


@strawberry.input
class RequestSortInput:
    field: RequestSortField = RequestSortField.CREATED_AT
    direction: SortDirection = SortDirection.ASC


@strawberry.input
class UserSortInput:
    field: UserSortField = UserSortField.CREATED_AT
    direction: SortDirection = SortDirection.ASC


@strawberry.input
class TransactionSortInput:
    field: TransactionSortField = TransactionSortField.CREATED_AT
    direction: SortDirection = SortDirection.ASC


#  фильтры
@strawberry.input
class RequestFilterInput:
    statuses: Optional[list[RequestStatus]] = None
    search: Optional[str] = None                 # поиск по описанию симптомов
    created_from: Optional[str] = None          
    created_to: Optional[str] = None
    has_expert: Optional[bool] = None


@strawberry.input
class UserFilterInput:
    role: Optional[Role] = None
    status: Optional[UserStatus] = None
    search: Optional[str] = None                 # по имени или email


@strawberry.input
class TransactionFilterInput:
    request_id: Optional[strawberry.ID] = None
    user_id: Optional[strawberry.ID] = None
    expert_id: Optional[strawberry.ID] = None
    status: Optional[str] = None                 # PENDING / SUCCESS / FAILED
    operation_type: Optional[str] = None         # PAYMENT / PAYOUT / REFUND
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    created_from: Optional[str] = None
    created_to: Optional[str] = None


@strawberry.input
class NotificationFilterInput:
    status: Optional[NotificationStatus] = None
    type: Optional[str] = None


@strawberry.input
class ApplicationFilterInput:
    status: Optional[ApplicationStatus] = None
    submitted_from: Optional[str] = None
    submitted_to: Optional[str] = None


#  бизнес-операции
@strawberry.input
class RegisterInput:
    email: str
    password: str
    name: str


@strawberry.input
class LoginInput:
    email: str
    password: str


@strawberry.input
class UpdateProfileInput:
    name: Optional[str] = None
    photo_url: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None


@strawberry.input
class ApplyForExpertInput:
    documents_url: str


@strawberry.input
class CreateRequestInput:
    symptoms: str
    photo_urls: list[str] = strawberry.field(default_factory=list)


@strawberry.input
class RespondToRequestInput:
    request_id: strawberry.ID
    comment: Optional[str] = None


@strawberry.input
class TreatmentStepInput:
    step: str
    frequency: Optional[str] = None
    duration_days: Optional[int] = None


@strawberry.input
class CreateDiagnosisInput:
    request_id: strawberry.ID
    disease_id: strawberry.ID
    description: str
    duration_days: int = 14
    checklist: list[TreatmentStepInput] = strawberry.field(default_factory=list)


@strawberry.input
class AddTreatmentStepInput:
    diagnosis_id: strawberry.ID
    step: str
    frequency: Optional[str] = None
    duration_days: Optional[int] = None


@strawberry.input
class UpdateTreatmentInput:
    change_description: str
    new_stage: Optional[str] = None


@strawberry.input
class SendMessageInput:
    chat_room_id: strawberry.ID
    text: Optional[str] = None
    attachment_url: Optional[str] = None


@strawberry.input
class CreatePaymentInput:
    request_id: strawberry.ID
    idempotency_key: str


@strawberry.input
class WithdrawalInput:
    amount: float


@strawberry.input
class CreateFieldInput:
    name: str
    geometry: str                              
