from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .utils import fmt_dt as _fmt, parse_uuid as _parse_uuid
from .errors import InvalidValueError, NotFoundError
from .models import Disease, Request
from .repository import DiseaseRepository, RequestRepository
from .schemas import DiseaseDTO, PhotoDTO, RequestDetailsDTO, RequestDTO

REQUEST_STATUSES = {"CREATED", "PENDING", "IN_PROGRESS", "DONE", "CANCELLED"}


def _to_request_dto(r: Request) -> RequestDTO:
    return RequestDTO(
        id=str(r.id),
        client_id=str(r.client_id),
        expert_id=str(r.expert_id) if r.expert_id else None,
        symptoms=r.symptoms,
        ai_prediagnosis=r.ai_prediagnosis,
        status=r.status,
        created_at=_fmt(r.created_at),
        completed_at=_fmt(r.completed_at),
        photos=[PhotoDTO(id=str(p.id), url=p.url, uploaded_at=_fmt(p.uploaded_at)) for p in r.photos],
    )


def _to_disease_dto(d: Disease) -> DiseaseDTO:
    return DiseaseDTO(id=str(d.id), name=d.name, description=d.description,
                      symptoms=d.symptoms, treatment=d.treatment)


class RequestService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    def get_request(self, request_id: str) -> RequestDTO:
        rid = _parse_uuid(request_id)
        with self._session_factory() as session:
            req = RequestRepository(session).get_by_id(rid)
            if req is None:
                raise NotFoundError(f"Заявка {request_id} не найдена")
            return _to_request_dto(req)

    def get_request_details(self, request_id: str) -> RequestDetailsDTO:
        req = self.get_request(request_id)
        return RequestDetailsDTO(request=req,
                                 photo_urls=[p.url for p in req.photos],
                                 ai_prediagnosis=req.ai_prediagnosis)

    def list_requests(self, client_id: Optional[str] = None, expert_id: Optional[str] = None,
                      status: Optional[str] = None) -> list[RequestDTO]:
        if status is not None and status not in REQUEST_STATUSES:
            raise InvalidValueError(f"Неизвестный статус заявки: {status}")
        cid = _parse_uuid(client_id) if client_id else None
        eid = _parse_uuid(expert_id) if expert_id else None
        with self._session_factory() as session:
            items = RequestRepository(session).list_requests(cid, eid, status)
            return [_to_request_dto(r) for r in items]

    def list_available_requests(self) -> list[RequestDTO]:
        return self.list_requests(status="CREATED")

    def get_disease(self, disease_id: str) -> DiseaseDTO:
        did = _parse_uuid(disease_id)
        with self._session_factory() as session:
            disease = DiseaseRepository(session).get_by_id(did)
            if disease is None:
                raise NotFoundError(f"Болезнь {disease_id} не найдена")
            return _to_disease_dto(disease)

    def list_diseases(self) -> list[DiseaseDTO]:
        with self._session_factory() as session:
            return [_to_disease_dto(d) for d in DiseaseRepository(session).list_all()]
