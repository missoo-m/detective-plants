
from enum import Enum
from typing import Optional

import strawberry

from . import clients
from .clients.base import NotFoundError


#  типы enum

@strawberry.enum
class Role(Enum):
    CLIENT = "CLIENT"
    EXPERT = "EXPERT"
    ADMIN = "ADMIN"


@strawberry.enum
class UserStatus(Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    PENDING = "PENDING"


@strawberry.enum
class RequestStatus(Enum):
    CREATED = "CREATED"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


@strawberry.enum
class ResponseStatus(Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


@strawberry.enum
class TrackerStatus(Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@strawberry.enum
class HistoryRecordType(Enum):
    PHOTO = "PHOTO"
    TREATMENT_UPDATE = "TREATMENT_UPDATE"


@strawberry.enum
class ChatStatus(Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


@strawberry.enum
class NotificationStatus(Enum):
    UNREAD = "UNREAD"
    READ = "READ"


@strawberry.enum
class ApplicationStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


#  типы
@strawberry.type
class Profile:
    id: strawberry.ID
    photo_url: Optional[str]
    description: Optional[str]
    rating: float
    language: str


@strawberry.type
class User:
    id: strawberry.ID
    email: str
    name: str
    role: Role
    status: UserStatus
    profile: Optional[Profile]
    created_at: str


@strawberry.type
class RequestPhoto:
    id: strawberry.ID
    url: str
    uploaded_at: str


@strawberry.type
class Disease:
    id: strawberry.ID
    name: str
    description: Optional[str]
    symptoms: Optional[str]
    treatment: Optional[str]


@strawberry.type
class TreatmentStep:
    id: strawberry.ID
    step: str
    frequency: Optional[str]
    duration_days: Optional[int]


@strawberry.type
class ExpertResponse:
    id: strawberry.ID
    comment: Optional[str]
    status: ResponseStatus
    created_at: str
    expert_id: strawberry.Private[str]

    @strawberry.field
    def expert(self) -> User:
        return to_user(clients.auth_client.get_user(self.expert_id))


@strawberry.type
class Diagnosis:
    id: strawberry.ID
    description: Optional[str]
    ai_prediagnosis: Optional[str]
    checklist: list[TreatmentStep]
    created_at: str
    request_id: strawberry.Private[str]
    expert_id: strawberry.Private[str]
    disease_id: strawberry.Private[str]

    @strawberry.field
    def request(self) -> "Request":
        return to_request(clients.request_client.get_request(self.request_id))

    @strawberry.field
    def expert(self) -> User:
        return to_user(clients.auth_client.get_user(self.expert_id))

    @strawberry.field
    def disease(self) -> Disease:
        return to_disease(clients.request_client.get_disease(self.disease_id))


@strawberry.type
class Request:
    id: strawberry.ID
    symptoms: str
    ai_prediagnosis: Optional[str]
    status: RequestStatus
    photos: list[RequestPhoto]
    created_at: str
    completed_at: Optional[str]
    client_id: strawberry.Private[str]
    expert_id: strawberry.Private[Optional[str]]

    @strawberry.field
    def client(self) -> User:
        return to_user(clients.auth_client.get_user(self.client_id))

    @strawberry.field
    def expert(self) -> Optional[User]:
        if not self.expert_id:
            return None
        return to_user(clients.auth_client.get_user(self.expert_id))

    @strawberry.field
    def responses(self) -> list[ExpertResponse]:
        return [to_expert_response(r) for r in clients.expert_client.list_responses(self.id)]

    @strawberry.field
    def diagnosis(self) -> Optional[Diagnosis]:
        try:
            return to_diagnosis(clients.expert_client.get_diagnosis_by_request(self.id))
        except NotFoundError:
            return None  


@strawberry.type
class TreatmentHistory:
    id: strawberry.ID
    record_type: HistoryRecordType
    date: str
    photo_url: Optional[str]
    change_description: Optional[str]
    author_id: strawberry.Private[str]

    @strawberry.field
    def author(self) -> User:
        return to_user(clients.auth_client.get_user(self.author_id))


@strawberry.type
class RecoveryTracker:
    id: strawberry.ID
    start_date: str
    end_date: Optional[str]
    status: TrackerStatus
    current_stage: Optional[str]
    history: list[TreatmentHistory]
    request_id: strawberry.Private[str]

    @strawberry.field
    def request(self) -> Request:
        return to_request(clients.request_client.get_request(self.request_id))


@strawberry.type
class Message:
    id: strawberry.ID
    text: Optional[str]
    attachment_url: Optional[str]
    is_read: bool
    sent_at: str
    sender_id: strawberry.Private[str]

    @strawberry.field
    def sender(self) -> User:
        return to_user(clients.auth_client.get_user(self.sender_id))


@strawberry.type
class ChatRoom:
    id: strawberry.ID
    status: ChatStatus
    created_at: str
    request_id: strawberry.Private[str]
    client_id: strawberry.Private[str]
    expert_id: strawberry.Private[str]

    @strawberry.field
    def request(self) -> Request:
        return to_request(clients.request_client.get_request(self.request_id))

    @strawberry.field
    def client(self) -> User:
        return to_user(clients.auth_client.get_user(self.client_id))

    @strawberry.field
    def expert(self) -> User:
        return to_user(clients.auth_client.get_user(self.expert_id))

    @strawberry.field
    def messages(self) -> list[Message]:
        return [to_message(m) for m in clients.chat_client.list_messages(self.id)]


@strawberry.type
class Notification:
    id: strawberry.ID
    type: str
    message: str
    status: NotificationStatus
    created_at: str


@strawberry.type
class Transaction:
    id: strawberry.ID
    amount: float
    operation_type: str
    status: str
    created_at: str
    request_id: strawberry.Private[str]
    user_id: strawberry.Private[str]

    @strawberry.field
    def request(self) -> Request:
        return to_request(clients.request_client.get_request(self.request_id))

    @strawberry.field
    def user(self) -> User:
        return to_user(clients.auth_client.get_user(self.user_id))


@strawberry.type
class Withdrawal:
    id: strawberry.ID
    amount: float
    status: str
    created_at: str
    processed_at: Optional[str]
    expert_id: strawberry.Private[str]

    @strawberry.field
    def expert(self) -> User:
        return to_user(clients.auth_client.get_user(self.expert_id))


@strawberry.type
class ExpertApplication:
    id: strawberry.ID
    documents_url: Optional[str]
    status: ApplicationStatus
    submitted_at: str
    verified_at: Optional[str]
    user_id: strawberry.Private[str]

    @strawberry.field
    def user(self) -> User:
        return to_user(clients.auth_client.get_user(self.user_id))


@strawberry.type
class ExpertStats:
    expert_id: strawberry.ID
    total_requests: int
    completed_requests: int
    avg_rating: float


@strawberry.type
class DiseaseStats:
    disease_id: strawberry.ID
    count: int
    period: str


@strawberry.type
class NdviMeasurement:
    id: strawberry.ID
    ndvi_value: float
    measured_at: str


@strawberry.type
class SatelliteAlert:
    id: strawberry.ID
    type: str
    message: str
    created_at: str


@strawberry.type
class SatelliteField:
    id: strawberry.ID
    name: str
    geometry: str
    created_at: str
    owner_id: strawberry.Private[str]

    @strawberry.field
    def owner(self) -> User:
        return to_user(clients.auth_client.get_user(self.owner_id))

    @strawberry.field
    def measurements(self) -> list[NdviMeasurement]:
        return [to_measurement(m) for m in clients.satellite_client.list_measurements(self.id)]

    @strawberry.field
    def alerts(self) -> list[SatelliteAlert]:
        return [to_alert(a) for a in clients.satellite_client.list_alerts(self.id)]


#  мапперы
def to_profile(d: Optional[dict]) -> Optional[Profile]:
    if not d:
        return None
    return Profile(id=d["id"], photo_url=d.get("photo_url"), description=d.get("description"),
                   rating=d.get("rating") or 0.0, language=d.get("language") or "ru")


def to_user(d: dict) -> User:
    return User(id=d["id"], email=d["email"], name=d["name"], role=Role(d["role"]),
                status=UserStatus(d["status"]), profile=to_profile(d.get("profile")),
                created_at=d["created_at"])


def to_disease(d: dict) -> Disease:
    return Disease(id=d["id"], name=d["name"], description=d.get("description"),
                   symptoms=d.get("symptoms"), treatment=d.get("treatment"))


def to_request(d: dict) -> Request:
    return Request(
        id=d["id"], symptoms=d["symptoms"], ai_prediagnosis=d.get("ai_prediagnosis"),
        status=RequestStatus(d["status"]),
        photos=[RequestPhoto(id=p["id"], url=p["url"], uploaded_at=p["uploaded_at"])
                for p in d.get("photos", [])],
        created_at=d["created_at"], completed_at=d.get("completed_at"),
        client_id=d["client_id"], expert_id=d.get("expert_id"),
    )


def to_expert_response(d: dict) -> ExpertResponse:
    return ExpertResponse(id=d["id"], comment=d.get("comment"), status=ResponseStatus(d["status"]),
                          created_at=d["created_at"], expert_id=d["expert_id"])


def to_diagnosis(d: dict) -> Diagnosis:
    return Diagnosis(
        id=d["id"], description=d.get("description"), ai_prediagnosis=d.get("ai_prediagnosis"),
        checklist=[TreatmentStep(id=s["id"], step=s["step"], frequency=s.get("frequency"),
                                 duration_days=s.get("duration_days")) for s in d.get("checklist", [])],
        created_at=d["created_at"], request_id=d["request_id"],
        expert_id=d["expert_id"], disease_id=d["disease_id"],
    )


def to_tracker(d: dict) -> RecoveryTracker:
    return RecoveryTracker(
        id=d["id"], start_date=d["start_date"], end_date=d.get("end_date"),
        status=TrackerStatus(d["status"]), current_stage=d.get("current_stage"),
        history=[TreatmentHistory(id=h["id"], record_type=HistoryRecordType(h["record_type"]),
                                  date=h["date"], photo_url=h.get("photo_url"),
                                  change_description=h.get("change_description"),
                                  author_id=h["author_id"]) for h in d.get("history", [])],
        request_id=d["request_id"],
    )


def to_message(d: dict) -> Message:
    return Message(id=d["id"], text=d.get("text"), attachment_url=d.get("attachment_url"),
                   is_read=d["is_read"], sent_at=d["sent_at"], sender_id=d["sender_id"])


def to_chat_room(d: dict) -> ChatRoom:
    return ChatRoom(id=d["id"], status=ChatStatus(d["status"]), created_at=d["created_at"],
                    request_id=d["request_id"], client_id=d["client_id"], expert_id=d["expert_id"])


def to_notification(d: dict) -> Notification:
    return Notification(id=d["id"], type=d["type"], message=d["message"],
                        status=NotificationStatus(d["status"]), created_at=d["created_at"])


def to_transaction(d: dict) -> Transaction:
    return Transaction(id=d["id"], amount=d["amount"], operation_type=d["operation_type"],
                       status=d["status"], created_at=d["created_at"],
                       request_id=d["request_id"], user_id=d["user_id"])


def to_withdrawal(d: dict) -> Withdrawal:
    return Withdrawal(id=d["id"], amount=d["amount"], status=d["status"], created_at=d["created_at"],
                      processed_at=d.get("processed_at"), expert_id=d["expert_id"])


def to_application(d: dict) -> ExpertApplication:
    return ExpertApplication(id=d["id"], documents_url=d.get("documents_url"),
                             status=ApplicationStatus(d["status"]), submitted_at=d["submitted_at"],
                             verified_at=d.get("verified_at"), user_id=d["user_id"])


def to_expert_stats(d: dict) -> ExpertStats:
    return ExpertStats(expert_id=d["expert_id"], total_requests=d["total_requests"],
                       completed_requests=d["completed_requests"], avg_rating=d["avg_rating"])


def to_disease_stats(d: dict) -> DiseaseStats:
    return DiseaseStats(disease_id=d["disease_id"], count=d["count"], period=d["period"])


def to_measurement(d: dict) -> NdviMeasurement:
    return NdviMeasurement(id=d["id"], ndvi_value=d["ndvi_value"], measured_at=d["measured_at"])


def to_alert(d: dict) -> SatelliteAlert:
    return SatelliteAlert(id=d["id"], type=d["type"], message=d["message"], created_at=d["created_at"])


def to_field(d: dict) -> SatelliteField:
    return SatelliteField(id=d["id"], name=d["name"], geometry=d["geometry"],
                          created_at=d["created_at"], owner_id=d["owner_id"])
