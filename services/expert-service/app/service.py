from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .utils import fmt_dt as _fmt, parse_uuid as _parse_uuid
from .errors import InvalidValueError, NotFoundError
from .models import Diagnosis, ExpertResponse
from .repository import DiagnosisRepository, ResponseRepository
from .schemas import DiagnosisDTO, ResponseDTO, TreatmentStepDTO


def _to_response_dto(r: ExpertResponse) -> ResponseDTO:
    return ResponseDTO(id=str(r.id), request_id=str(r.request_id), expert_id=str(r.expert_id),
                       comment=r.comment, status=r.status, created_at=_fmt(r.created_at))


def _to_diagnosis_dto(d: Diagnosis) -> DiagnosisDTO:
    return DiagnosisDTO(
        id=str(d.id), request_id=str(d.request_id), expert_id=str(d.expert_id),
        disease_id=str(d.disease_id), description=d.description,
        ai_prediagnosis=d.ai_prediagnosis, duration_days=d.duration_days or 14,
        created_at=_fmt(d.created_at),
        checklist=[TreatmentStepDTO(id=str(s.id), step=s.step, frequency=s.frequency,
                                    duration_days=s.duration_days) for s in d.checklist],
    )


class ExpertService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    def list_responses(self, request_id: str) -> list[ResponseDTO]:
        rid = _parse_uuid(request_id)
        with self._session_factory() as session:
            return [_to_response_dto(r) for r in ResponseRepository(session).list_by_request(rid)]

    def list_responses_by_expert(self, expert_id: str) -> list[ResponseDTO]:
        eid = _parse_uuid(expert_id)
        with self._session_factory() as session:
            return [_to_response_dto(r) for r in ResponseRepository(session).list_by_expert(eid)]

    def get_diagnosis(self, diagnosis_id: str) -> DiagnosisDTO:
        did = _parse_uuid(diagnosis_id)
        with self._session_factory() as session:
            diagnosis = DiagnosisRepository(session).get_by_id(did)
            if diagnosis is None:
                raise NotFoundError(f"Диагноз {diagnosis_id} не найден")
            return _to_diagnosis_dto(diagnosis)

    def get_diagnosis_by_request(self, request_id: str) -> DiagnosisDTO:
        rid = _parse_uuid(request_id)
        with self._session_factory() as session:
            diagnosis = DiagnosisRepository(session).get_by_request(rid)
            if diagnosis is None:
                raise NotFoundError(f"Для заявки {request_id} диагноз ещё не поставлен")
            return _to_diagnosis_dto(diagnosis)
