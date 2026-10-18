import strawberry
from strawberry.file_uploads import Upload
from strawberry.types import Info

from . import clients
from .api_types import (
    AuthPayload, Diagnosis, ExpertApplication, ExpertResponse, Message, Notification, Profile, RecoveryTracker,
    Request, RequestPhoto, SatelliteField, TreatmentHistory, TreatmentStep, Transaction, User, VideoRoom, Withdrawal,
    to_application, to_auth_payload, to_diagnosis, to_expert_response, to_field, to_history, to_message,
    to_notification, to_photo, to_profile, to_request, to_step, to_tracker, to_transaction, to_user, to_video_room,
    to_withdrawal,
)
from .errors import AuthenticationError
from .inputs import (
    AddTreatmentStepInput, ApplyForExpertInput, CreateDiagnosisInput, CreateFieldInput, CreatePaymentInput,
    CreateRequestInput, LoginInput, RegisterInput, RespondToRequestInput, SendMessageInput, UpdateProfileInput,
    UpdateTreatmentInput, WithdrawalInput,
)
from .security.access import identity_of
from .security.permissions import access


def _mutation(operation: str):
    return strawberry.mutation(permission_classes=[access(operation)])


def _actor(info: Info) -> str:
    return identity_of(info).user_id


def _role(info: Info) -> str:
    return identity_of(info).role


def read_upload(file) -> tuple:
    stream = getattr(file, "file", file)
    return file.filename, stream.read()


@strawberry.type
class Mutation:
    @_mutation("Mutation.register")
    def register(self, input: RegisterInput) -> AuthPayload:
        clients.security_client.register(input.email, input.password, input.name)
        return to_auth_payload(clients.security_client.login(input.email, input.password))

    @_mutation("Mutation.login")
    def login(self, input: LoginInput) -> AuthPayload:
        #Auth Service проверяет пароль, создаёт сессию в Redis и выдаёт JWT
        return to_auth_payload(clients.security_client.login(input.email, input.password))

    @_mutation("Mutation.logout")
    def logout(self, info: Info) -> bool:
        #Выход: сессия удаляется из Redis, токен перестаёт действовать
        token = info.context.get("token")
        if not token:
            raise AuthenticationError("Токен не передан")
        return clients.security_client.logout(token)

    @_mutation("Mutation.updateProfile")
    def update_profile(self, info: Info, input: UpdateProfileInput) -> Profile:
        user = clients.auth_client.update_profile(_actor(info), input.name, input.photo_url, input.description,
                                                  input.language)
        return to_profile(user["profile"])

    @_mutation("Mutation.applyForExpert")
    def apply_for_expert(self, info: Info, input: ApplyForExpertInput) -> ExpertApplication:
        return to_application(clients.admin_client.submit_application(_actor(info), input.documents_url, _role(info)))

    @_mutation("Mutation.createRequest")
    def create_request(self, info: Info, input: CreateRequestInput) -> Request:
        return to_request(clients.request_client.create_request(_actor(info), input.symptoms, input.photo_urls,
                                                                _role(info)))

    @_mutation("Mutation.uploadRequestPhoto")
    def upload_request_photo(self, info: Info, request_id: strawberry.ID, file: Upload) -> RequestPhoto:
        name, content = read_upload(file)
        return to_photo(clients.request_client.add_photo(request_id, _actor(info), name, content))

    @_mutation("Mutation.respondToRequest")
    def respond_to_request(self, info: Info, input: RespondToRequestInput) -> ExpertResponse:
        return to_expert_response(clients.expert_client.respond_to_request(
            input.request_id, _actor(info), input.comment, _role(info)))

    @_mutation("Mutation.selectExpert")
    def select_expert(self, info: Info, request_id: strawberry.ID, expert_id: strawberry.ID) -> Request:
        return to_request(clients.request_client.select_expert(request_id, _actor(info), expert_id))

    @_mutation("Mutation.cancelRequest")
    def cancel_request(self, info: Info, request_id: strawberry.ID) -> Request:
        return to_request(clients.request_client.cancel_request(request_id, _actor(info)))

    @_mutation("Mutation.createPayment")
    def create_payment(self, info: Info, input: CreatePaymentInput) -> Transaction:
        return to_transaction(clients.payment_client.create_payment(
            input.request_id, _actor(info), input.idempotency_key, _role(info)))

    @_mutation("Mutation.requestWithdrawal")
    def request_withdrawal(self, info: Info, input: WithdrawalInput) -> Withdrawal:
        return to_withdrawal(clients.payment_client.request_withdrawal(_actor(info), input.amount, _role(info)))

    @_mutation("Mutation.approveWithdrawal")
    def approve_withdrawal(self, info: Info, withdrawal_id: strawberry.ID) -> Withdrawal:
        return to_withdrawal(clients.payment_client.approve_withdrawal(withdrawal_id, _actor(info), _role(info)))

    @_mutation("Mutation.createDiagnosis")
    def create_diagnosis(self, info: Info, input: CreateDiagnosisInput) -> Diagnosis:
        checklist = [{"step": s.step, "frequency": s.frequency, "duration_days": s.duration_days}
                     for s in input.checklist]
        return to_diagnosis(clients.expert_client.create_diagnosis(
            input.request_id, _actor(info), input.disease_id, input.description, input.duration_days, checklist,
            _role(info)))

    @_mutation("Mutation.addTreatmentStep")
    def add_treatment_step(self, info: Info, input: AddTreatmentStepInput) -> TreatmentStep:
        return to_step(clients.expert_client.add_treatment_step(
            input.diagnosis_id, _actor(info), input.step, input.frequency, input.duration_days))

    @_mutation("Mutation.uploadTrackerPhoto")
    def upload_tracker_photo(self, info: Info, tracker_id: strawberry.ID, file: Upload) -> TreatmentHistory:
        name, content = read_upload(file)
        return to_history(clients.recovery_client.upload_photo(tracker_id, _actor(info), name, content))

    @_mutation("Mutation.updateTreatment")
    def update_treatment(self, info: Info, tracker_id: strawberry.ID, input: UpdateTreatmentInput) -> TreatmentHistory:
        return to_history(clients.recovery_client.update_treatment(tracker_id, _actor(info),
                                                                   input.change_description, input.new_stage))

    @_mutation("Mutation.completeTracker")
    def complete_tracker(self, info: Info, tracker_id: strawberry.ID) -> RecoveryTracker:
        return to_tracker(clients.recovery_client.complete_tracker(tracker_id, _actor(info)))

    @_mutation("Mutation.sendMessage")
    def send_message(self, info: Info, input: SendMessageInput) -> Message:
        return to_message(clients.chat_client.send_message(input.chat_room_id, _actor(info), input.text,
                                                           input.attachment_url))

    @_mutation("Mutation.markMessageRead")
    def mark_message_read(self, info: Info, message_id: strawberry.ID) -> Message:
        return to_message(clients.chat_client.mark_read(message_id, _actor(info)))

    @_mutation("Mutation.createVideoRoom")
    def create_video_room(self, info: Info, chat_room_id: strawberry.ID) -> VideoRoom:
        return to_video_room(clients.chat_client.create_video_room(chat_room_id, _actor(info)))

    @_mutation("Mutation.markNotificationRead")
    def mark_notification_read(self, info: Info, notification_id: strawberry.ID) -> Notification:
        return to_notification(clients.notification_client.mark_read(notification_id, _actor(info)))

    @_mutation("Mutation.markAllNotificationsRead")
    def mark_all_notifications_read(self, info: Info) -> int:
        return clients.notification_client.mark_all_read(_actor(info))

    @_mutation("Mutation.verifyExpert")
    def verify_expert(self, info: Info, application_id: strawberry.ID, approve: bool) -> ExpertApplication:
        return to_application(clients.admin_client.verify_expert(application_id, _actor(info), approve, _role(info)))

    @_mutation("Mutation.blockUser")
    def block_user(self, info: Info, user_id: strawberry.ID) -> User:
        clients.admin_client.block_user(_actor(info), user_id, _role(info))
        return to_user(clients.auth_client.get_user(user_id))

    @_mutation("Mutation.createField")
    def create_field(self, info: Info, input: CreateFieldInput) -> SatelliteField:
        return to_field(clients.satellite_client.create_field(_actor(info), input.name, input.geometry))
