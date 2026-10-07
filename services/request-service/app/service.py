import os
import uuid
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy.orm import Session

from . import config
from .clients import AiClient, AuthClient, ExpertClient, MockAiClient, MockAuthClient, MockExpertClient, \
    MockStorageClient, StorageClient
from .database import get_session_factory
from .errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from .models import Disease, Request, RequestPhoto, utcnow
from .repository import SORT_COLUMNS, DiseaseRepository, RequestRepository
from .schemas import DiseaseDTO, PhotoDTO, RequestDetailsDTO, RequestDTO, RequestsSummaryDTO
from .utils import fmt_dt, parse_uuid

REQUEST_STATUSES = {"CREATED", "PENDING", "IN_PROGRESS", "DONE", "CANCELLED"}
ACTIVE_STATUSES = ["CREATED", "PENDING", "IN_PROGRESS"]
TRANSITIONS = {
    "CREATED": {"PENDING", "CANCELLED"},
    "PENDING": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"DONE"},
    "DONE": set(),
    "CANCELLED": set(),
}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _to_request_dto(r: Request) -> RequestDTO:
    return RequestDTO(
        id=str(r.id), client_id=str(r.client_id), expert_id=str(r.expert_id) if r.expert_id else None,
        symptoms=r.symptoms, ai_prediagnosis=r.ai_prediagnosis, status=r.status,
        created_at=fmt_dt(r.created_at), completed_at=fmt_dt(r.completed_at),
        photos=[PhotoDTO(id=str(p.id), url=p.url, uploaded_at=fmt_dt(p.uploaded_at)) for p in r.photos])


def _to_disease_dto(d: Disease) -> DiseaseDTO:
    return DiseaseDTO(id=str(d.id), name=d.name, description=d.description, symptoms=d.symptoms, treatment=d.treatment)


class RequestService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None, auth: Optional[AuthClient] = None,
                 expert: Optional[ExpertClient] = None, storage: Optional[StorageClient] = None,
                 ai: Optional[AiClient] = None):
        self._session_factory = session_factory or get_session_factory()
        self._auth = auth or MockAuthClient()
        self._expert = expert or MockExpertClient()
        self._storage = storage or MockStorageClient()
        self._ai = ai or MockAiClient()

    def _require_active_user(self, user_id: str, role: str) -> None:
        user = self._auth.get_user(user_id)
        if user["status"] != "ACTIVE":
            raise PermissionDeniedError("Учётная запись пользователя заблокирована или не активна")
        if user["role"] != role:
            raise PermissionDeniedError(f"Действие доступно только роли {role}")

    @staticmethod
    def _load(repo: RequestRepository, request_id: str) -> Request:
        req = repo.get_by_id(parse_uuid(request_id))
        if req is None:
            raise NotFoundError(f"Заявка {request_id} не найдена")
        return req

    @staticmethod
    def _change_status(req: Request, new_status: str) -> None:
        if new_status not in TRANSITIONS[req.status]:
            raise BusinessRuleError(f"Недопустимый переход статуса заявки: {req.status} → {new_status}")
        req.status = new_status
        if new_status in ("DONE", "CANCELLED"):
            req.completed_at = utcnow()

    def get_request(self, request_id: str) -> RequestDTO:
        with self._session_factory() as session:
            return _to_request_dto(self._load(RequestRepository(session), request_id))

    def get_request_details(self, request_id: str) -> RequestDetailsDTO:
        req = self.get_request(request_id)
        return RequestDetailsDTO(request=req, photo_urls=[p.url for p in req.photos],
                                 ai_prediagnosis=req.ai_prediagnosis)

    def list_requests(self, client_id: Optional[str] = None, expert_id: Optional[str] = None,
                      statuses: Optional[list] = None, status: Optional[str] = None,
                      search: Optional[str] = None, created_from: Optional[datetime] = None,
                      created_to: Optional[datetime] = None, has_expert: Optional[bool] = None,
                      sort_by: str = "created_at", descending: bool = False,
                      limit: Optional[int] = None, offset: int = 0) -> list[RequestDTO]:
        statuses = list(statuses or ([status] if status else []))
        for s in statuses:
            if s not in REQUEST_STATUSES:
                raise InvalidValueError(f"Неизвестный статус заявки: {s}")
        if sort_by not in SORT_COLUMNS:
            raise InvalidValueError(f"Сортировка по полю {sort_by} не поддерживается")
        if created_from and created_to and created_from > created_to:
            raise InvalidValueError("Начало периода не может быть позже его конца")
        if (limit is not None and limit < 1) or offset < 0:
            raise InvalidValueError("limit должен быть больше 0, offset не может быть отрицательным")
        cid = parse_uuid(client_id) if client_id else None
        eid = parse_uuid(expert_id) if expert_id else None
        with self._session_factory() as session:
            items = RequestRepository(session).list_requests(
                cid, eid, statuses, search, created_from, created_to, has_expert, sort_by, descending, limit, offset)
            return [_to_request_dto(r) for r in items]

    def list_available_requests(self, **kwargs) -> list[RequestDTO]:
        kwargs.pop("statuses", None)
        kwargs.pop("status", None)
        return self.list_requests(statuses=["CREATED"], **kwargs)

    def requests_summary(self, client_id: Optional[str] = None, expert_id: Optional[str] = None) -> RequestsSummaryDTO:
        cid = parse_uuid(client_id) if client_id else None
        eid = parse_uuid(expert_id) if expert_id else None
        with self._session_factory() as session:
            by_status = RequestRepository(session).count_by_status(cid, eid)
        return RequestsSummaryDTO(total=sum(by_status.values()), by_status=by_status)

    def get_disease(self, disease_id: str) -> DiseaseDTO:
        with self._session_factory() as session:
            disease = DiseaseRepository(session).get_by_id(parse_uuid(disease_id))
            if disease is None:
                raise NotFoundError(f"Болезнь {disease_id} не найдена")
            return _to_disease_dto(disease)

    def list_diseases(self) -> list[DiseaseDTO]:
        with self._session_factory() as session:
            return [_to_disease_dto(d) for d in DiseaseRepository(session).list_all()]

    def create_request(self, client_id: str, symptoms: str, photo_urls: Optional[list] = None) -> RequestDTO:
        symptoms = (symptoms or "").strip()
        photo_urls = list(photo_urls or [])
        if not 10 <= len(symptoms) <= 2000:
            raise InvalidValueError("Описание симптомов должно содержать от 10 до 2000 символов")
        if len(photo_urls) > config.MAX_PHOTOS:
            raise InvalidValueError(f"К заявке можно прикрепить не более {config.MAX_PHOTOS} фото")
        if any(not u.startswith(("http://", "https://")) for u in photo_urls):
            raise InvalidValueError("Ссылка на фото должна начинаться с http:// или https://")
        self._require_active_user(client_id, "CLIENT")
        cid = parse_uuid(client_id)
        with self._session_factory() as session:
            repo = RequestRepository(session)
            active = sum(repo.count_by_status(client_id=cid).get(s, 0) for s in ACTIVE_STATUSES)
            if active >= config.MAX_ACTIVE_REQUESTS:
                raise BusinessRuleError(
                    f"Нельзя иметь более {config.MAX_ACTIVE_REQUESTS} активных заявок одновременно")
            req = Request(client_id=cid, symptoms=symptoms, status="CREATED",
                          ai_prediagnosis=self._ai.prediagnose(symptoms))
            req.photos = [RequestPhoto(url=u) for u in photo_urls]
            repo.add(req)
            session.commit()
            return _to_request_dto(req)

    def add_photo(self, request_id: str, client_id: str, file_name: str, content: bytes) -> PhotoDTO:
        ext = os.path.splitext(file_name or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise InvalidValueError("Допустимы только файлы JPG и PNG")
        if not content:
            raise InvalidValueError("Файл пуст")
        if len(content) > config.MAX_FILE_BYTES:
            raise InvalidValueError("Размер файла не должен превышать 5 МБ")
        with self._session_factory() as session:
            req = self._load(RequestRepository(session), request_id)
            if str(req.client_id) != client_id:
                raise PermissionDeniedError("Добавлять фото может только автор заявки")
            if req.status not in ("CREATED", "PENDING"):
                raise BusinessRuleError("Фото можно добавлять только до начала работы эксперта")
            if len(req.photos) >= config.MAX_PHOTOS:
                raise BusinessRuleError(f"К заявке уже прикреплено {config.MAX_PHOTOS} фото")
            photo = RequestPhoto(request_id=req.id, url=self._storage.save(str(req.id), file_name, content))
            session.add(photo)
            session.commit()
            return PhotoDTO(id=str(photo.id), url=photo.url, uploaded_at=fmt_dt(photo.uploaded_at))

    def select_expert(self, request_id: str, client_id: str, expert_id: str) -> RequestDTO:
        parse_uuid(expert_id)
        with self._session_factory() as session:
            req = self._load(RequestRepository(session), request_id)
            if str(req.client_id) != client_id:
                raise PermissionDeniedError("Выбрать эксперта может только автор заявки")
            if req.status != "CREATED":
                raise BusinessRuleError(f"Эксперта можно выбрать только для новой заявки, сейчас статус {req.status}")
            self._require_active_user(expert_id, "EXPERT")
            if not self._expert.has_responded(request_id, expert_id):
                raise BusinessRuleError("Этот эксперт не откликался на заявку")
            req.expert_id = parse_uuid(expert_id)
            self._change_status(req, "PENDING")
            session.commit()
            result = _to_request_dto(req)
        self._expert.accept_response(request_id, expert_id)     
        return result

    def cancel_request(self, request_id: str, client_id: str) -> RequestDTO:
        with self._session_factory() as session:
            req = self._load(RequestRepository(session), request_id)
            if str(req.client_id) != client_id:
                raise PermissionDeniedError("Отменить заявку может только её автор")
            if req.status not in ("CREATED", "PENDING"):
                raise BusinessRuleError(
                    f"Заявку в статусе {req.status} отменить нельзя: отмена возможна до начала работы эксперта")
            self._change_status(req, "CANCELLED")
            session.commit()
            return _to_request_dto(req)

    def start_work(self, request_id: str) -> RequestDTO:
        with self._session_factory() as session:
            req = self._load(RequestRepository(session), request_id)
            self._change_status(req, "IN_PROGRESS")
            session.commit()
            return _to_request_dto(req)

    def complete_request(self, request_id: str) -> RequestDTO:
        with self._session_factory() as session:
            req = self._load(RequestRepository(session), request_id)
            self._change_status(req, "DONE")
            session.commit()
            return _to_request_dto(req)
