from typing import Callable, Optional

from sqlalchemy.orm import Session

from .clients import AuthClient, MockAuthClient, MockRecoveryClient, MockRequestClient, RecoveryClient, RequestClient
from .database import get_session_factory
from .errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from .models import Diagnosis, ExpertResponse, MLTrainingExample, TreatmentChecklist
from .repository import DiagnosisRepository, ResponseRepository
from .schemas import DiagnosisDTO, ResponseDTO, ResponsesSummaryDTO, TreatmentStepDTO
from .utils import fmt_dt, parse_uuid

RESPONSE_STATUSES = {"PENDING", "ACCEPTED", "REJECTED"}
MAX_STEPS = 20


def _to_response_dto(r: ExpertResponse) -> ResponseDTO:
    return ResponseDTO(id=str(r.id), request_id=str(r.request_id), expert_id=str(r.expert_id),
                       comment=r.comment, status=r.status, created_at=fmt_dt(r.created_at))


def _to_diagnosis_dto(d: Diagnosis) -> DiagnosisDTO:
    return DiagnosisDTO(
        id=str(d.id), request_id=str(d.request_id), expert_id=str(d.expert_id), disease_id=str(d.disease_id),
        description=d.description, ai_prediagnosis=d.ai_prediagnosis, duration_days=d.duration_days or 14,
        created_at=fmt_dt(d.created_at),
        checklist=[TreatmentStepDTO(id=str(s.id), step=s.step, frequency=s.frequency, duration_days=s.duration_days)
                   for s in d.checklist])


def _clean_step(step: dict) -> dict:
    text = (step.get("step") or "").strip()
    if not 3 <= len(text) <= 500:
        raise InvalidValueError("Шаг лечения должен содержать от 3 до 500 символов")
    days = step.get("duration_days")
    if days is not None and not 1 <= days <= 60:
        raise InvalidValueError("Длительность шага должна быть от 1 до 60 дней")
    return {"step": text, "frequency": step.get("frequency"), "duration_days": days}


class ExpertService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None, auth: Optional[AuthClient] = None,
                 requests: Optional[RequestClient] = None, recovery: Optional[RecoveryClient] = None):
        self._session_factory = session_factory or get_session_factory()
        self._auth = auth or MockAuthClient()
        self._requests = requests or MockRequestClient()
        self._recovery = recovery or MockRecoveryClient()

    def _require_expert(self, expert_id: str) -> None:
        user = self._auth.get_user(expert_id)
        if user["status"] != "ACTIVE":
            raise PermissionDeniedError("Учётная запись пользователя заблокирована или не активна")
        if user["role"] != "EXPERT":
            raise PermissionDeniedError("Действие доступно только эксперту")

    def list_responses(self, request_id: str) -> list[ResponseDTO]:
        rid = parse_uuid(request_id)
        with self._session_factory() as session:
            return [_to_response_dto(r) for r in ResponseRepository(session).list_by_request(rid)]

    def has_responded(self, request_id: str, expert_id: str) -> bool:
        rid, eid = parse_uuid(request_id), parse_uuid(expert_id)
        with self._session_factory() as session:
            return ResponseRepository(session).get(rid, eid) is not None

    def list_responses_by_expert(self, expert_id: str, status: Optional[str] = None,
                                 descending: bool = False) -> list[ResponseDTO]:
        if status is not None and status not in RESPONSE_STATUSES:
            raise InvalidValueError(f"Неизвестный статус отклика: {status}")
        eid = parse_uuid(expert_id)
        with self._session_factory() as session:
            return [_to_response_dto(r) for r in ResponseRepository(session).list_by_expert(eid, status, descending)]

    def responses_summary(self, expert_id: str) -> ResponsesSummaryDTO:
        eid = parse_uuid(expert_id)
        with self._session_factory() as session:
            by_status = ResponseRepository(session).count_by_status(eid)
        return ResponsesSummaryDTO(total=sum(by_status.values()), by_status=by_status)

    def get_diagnosis(self, diagnosis_id: str) -> DiagnosisDTO:
        did = parse_uuid(diagnosis_id)
        with self._session_factory() as session:
            diagnosis = DiagnosisRepository(session).get_by_id(did)
            if diagnosis is None:
                raise NotFoundError(f"Диагноз {diagnosis_id} не найден")
            return _to_diagnosis_dto(diagnosis)

    def get_diagnosis_by_request(self, request_id: str) -> DiagnosisDTO:
        rid = parse_uuid(request_id)
        with self._session_factory() as session:
            diagnosis = DiagnosisRepository(session).get_by_request(rid)
            if diagnosis is None:
                raise NotFoundError(f"Для заявки {request_id} диагноз ещё не поставлен")
            return _to_diagnosis_dto(diagnosis)

    def respond_to_request(self, request_id: str, expert_id: str, comment: Optional[str] = None) -> ResponseDTO:
        rid, eid = parse_uuid(request_id), parse_uuid(expert_id)
        comment = (comment or "").strip() or None
        if comment and len(comment) > 500:
            raise InvalidValueError("Комментарий не должен превышать 500 символов")
        self._require_expert(expert_id)
        request = self._requests.get_request_details(request_id)
        if request["status"] != "CREATED":
            raise BusinessRuleError(f"Откликнуться можно только на новую заявку, сейчас статус {request['status']}")
        with self._session_factory() as session:
            repo = ResponseRepository(session)
            if repo.get(rid, eid) is not None:
                raise BusinessRuleError("Вы уже откликнулись на эту заявку")
            response = ExpertResponse(request_id=rid, expert_id=eid, comment=comment, status="PENDING")
            repo.add(response)
            session.commit()
            return _to_response_dto(response)

    def accept_response(self, request_id: str, expert_id: str) -> list[ResponseDTO]:
        rid, eid = parse_uuid(request_id), parse_uuid(expert_id)
        with self._session_factory() as session:
            responses = ResponseRepository(session).list_by_request(rid)
            if not any(r.expert_id == eid for r in responses):
                raise BusinessRuleError("Эксперт не откликался на эту заявку")
            for r in responses:
                r.status = "ACCEPTED" if r.expert_id == eid else "REJECTED"
            session.commit()
            return [_to_response_dto(r) for r in responses]

    def create_diagnosis(self, request_id: str, expert_id: str, disease_id: str, description: str,
                         duration_days: int = 14, checklist: Optional[list] = None) -> DiagnosisDTO:
        rid, eid, did = parse_uuid(request_id), parse_uuid(expert_id), parse_uuid(disease_id)
        description = (description or "").strip()
        if not 5 <= len(description) <= 2000:
            raise InvalidValueError("Описание диагноза должно содержать от 5 до 2000 символов")
        if not 1 <= duration_days <= 60:
            raise InvalidValueError("Длительность лечения должна быть от 1 до 60 дней")
        steps = [_clean_step(s) for s in (checklist or [])]
        if len(steps) > MAX_STEPS:
            raise InvalidValueError(f"В чек-листе может быть не более {MAX_STEPS} шагов")
        self._require_expert(expert_id)
        request = self._requests.get_request_details(request_id)
        if request["expert_id"] != expert_id:
            raise PermissionDeniedError("Диагноз может поставить только эксперт, выбранный клиентом")
        if request["status"] != "IN_PROGRESS":
            raise BusinessRuleError("Диагноз можно поставить только по оплаченной заявке в работе")
        self._requests.get_disease(disease_id)                      # болезнь должна быть в справочнике
        with self._session_factory() as session:
            repo = DiagnosisRepository(session)
            if repo.get_by_request(rid) is not None:
                raise BusinessRuleError("Диагноз по этой заявке уже поставлен")
            diagnosis = Diagnosis(request_id=rid, expert_id=eid, disease_id=did, description=description,
                                  ai_prediagnosis=request.get("ai_prediagnosis"), duration_days=duration_days)
            diagnosis.checklist = [TreatmentChecklist(position=i + 1, **s) for i, s in enumerate(steps)]
            repo.add(diagnosis)
            ai = request.get("ai_prediagnosis")
            if ai and ai.strip().lower() != description.lower():
                repo.add_ml_example(MLTrainingExample(request_id=rid, ai_prediagnosis=ai, expert_correction=description))
            session.commit()
            result = _to_diagnosis_dto(diagnosis)
        self._recovery.create_tracker(request_id, request["client_id"], expert_id, duration_days)
        return result

    def add_treatment_step(self, diagnosis_id: str, expert_id: str, step: str, frequency: Optional[str] = None,
                           duration_days: Optional[int] = None) -> TreatmentStepDTO:
        did = parse_uuid(diagnosis_id)
        data = _clean_step({"step": step, "frequency": frequency, "duration_days": duration_days})
        with self._session_factory() as session:
            diagnosis = DiagnosisRepository(session).get_by_id(did)
            if diagnosis is None:
                raise NotFoundError(f"Диагноз {diagnosis_id} не найден")
            if str(diagnosis.expert_id) != expert_id:
                raise PermissionDeniedError("Изменять чек-лист может только автор диагноза")
            if len(diagnosis.checklist) >= MAX_STEPS:
                raise BusinessRuleError(f"В чек-листе уже {MAX_STEPS} шагов")
            item = TreatmentChecklist(diagnosis_id=diagnosis.id, position=len(diagnosis.checklist) + 1, **data)
            session.add(item)
            session.commit()
            return TreatmentStepDTO(id=str(item.id), step=item.step, frequency=item.frequency,
                                    duration_days=item.duration_days)
