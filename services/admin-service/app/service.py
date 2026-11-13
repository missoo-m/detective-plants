from datetime import datetime
import logging
from typing import Callable, Optional

from sqlalchemy.orm import Session

from .clients import AuthClient, GrpcAuthClient
from .database import get_session_factory
from .errors import (BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError,
                     ServiceUnavailableError)
from .events import add_event
from .models import ExpertApplication, utcnow
from .repository import ApplicationRepository
from .schemas import ApplicationDTO, ApplicationsSummaryDTO
from .utils import fmt_dt, parse_uuid

log = logging.getLogger("admin")
APPLICATION_STATUSES = {"PENDING", "APPROVED", "REJECTED"}


def _dto(a: ExpertApplication) -> ApplicationDTO:
    return ApplicationDTO(id=str(a.id), user_id=str(a.user_id), documents_url=a.documents_url, status=a.status,
                          submitted_at=fmt_dt(a.submitted_at), verified_at=fmt_dt(a.verified_at))


class AdminService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None, auth: Optional[AuthClient] = None):
        self._session_factory = session_factory or get_session_factory()
        self._auth = auth or GrpcAuthClient()

    def _require_admin(self, admin_id: str, actor_role: Optional[str] = None) -> None:
        if actor_role is not None:
            if actor_role != "ADMIN":
                raise PermissionDeniedError("Действие доступно только администратору")
            return
        user = self._auth.get_user(admin_id)
        if user["status"] != "ACTIVE" or user["role"] != "ADMIN":
            raise PermissionDeniedError("Действие доступно только администратору")

    def get_application(self, application_id: str) -> ApplicationDTO:
        with self._session_factory() as session:
            app = ApplicationRepository(session).get_by_id(parse_uuid(application_id))
            if app is None:
                raise NotFoundError(f"Заявка эксперта {application_id} не найдена")
            return _dto(app)

    def list_applications(self, status: Optional[str] = None, submitted_from: Optional[datetime] = None,
                          submitted_to: Optional[datetime] = None, descending: bool = True) -> list[ApplicationDTO]:
        if status is not None and status not in APPLICATION_STATUSES:
            raise InvalidValueError(f"Неизвестный статус заявки эксперта: {status}")
        if submitted_from and submitted_to and submitted_from > submitted_to:
            raise InvalidValueError("Начало периода не может быть позже его конца")
        with self._session_factory() as session:
            items = ApplicationRepository(session).list_applications(status, submitted_from, submitted_to, descending)
            return [_dto(a) for a in items]

    def applications_summary(self) -> ApplicationsSummaryDTO:
        with self._session_factory() as session:
            by_status = ApplicationRepository(session).count_by_status()
        return ApplicationsSummaryDTO(total=sum(by_status.values()), by_status=by_status)

    def submit_application(self, user_id: str, documents_url: str, actor_role: Optional[str] = None) -> ApplicationDTO:
        url = (documents_url or "").strip()
        if not url.startswith(("http://", "https://")) or len(url) > 500:
            raise InvalidValueError("documents_url должен быть ссылкой http(s) длиной до 500 символов")
        uid = parse_uuid(user_id)
        if actor_role is None:
            user = self._auth.get_user(user_id)
            if user["status"] != "ACTIVE":
                raise PermissionDeniedError("Учётная запись пользователя заблокирована или не активна")
            actor_role = user["role"]
        if actor_role != "CLIENT":
            raise BusinessRuleError("Подать заявку может только пользователь с ролью CLIENT")
        with self._session_factory() as session:
            repo = ApplicationRepository(session)
            app = repo.get_by_user(uid)
            if app is not None and app.status in ("PENDING", "APPROVED"):
                raise BusinessRuleError(f"Заявка уже существует (статус {app.status})")
            if app is None:
                app = ExpertApplication(user_id=uid)
                repo.add(app)
            app.documents_url, app.status = url, "PENDING"
            app.submitted_at, app.verified_at = utcnow(), None
            session.commit()
            return _dto(app)

    def verify_expert(self, application_id: str, admin_id: str, approve: bool,
                      actor_role: Optional[str] = None) -> ApplicationDTO:
        self._require_admin(admin_id, actor_role)
        with self._session_factory() as session:
            app = ApplicationRepository(session).get_by_id(parse_uuid(application_id))
            if app is None:
                raise NotFoundError(f"Заявка эксперта {application_id} не найдена")
            if app.status != "PENDING":
                raise BusinessRuleError(f"Заявка уже рассмотрена (статус {app.status})")
            app.status = "APPROVED" if approve else "REJECTED"
            app.verified_at = utcnow()
            result, user_id = _dto(app), str(app.user_id)
            if approve:
                add_event(session, "ExpertVerified", {"application_id": result.id, "user_id": user_id,
                                                      "admin_id": admin_id, "verified_at": result.verified_at})
            session.commit()
        if approve:
            try:
                self._auth.assign_role(user_id, "EXPERT")
            except ServiceUnavailableError as error:
                log.warning("Auth Service недоступен, роль EXPERT будет выдана по событию: %s", error)
        return result

    def block_user(self, admin_id: str, user_id: str, actor_role: Optional[str] = None) -> dict:
        self._require_admin(admin_id, actor_role)
        parse_uuid(user_id)
        target = self._auth.get_user(user_id)
        if target["role"] == "ADMIN":
            raise BusinessRuleError("Администратора заблокировать нельзя")
        if target["status"] == "BLOCKED":
            raise BusinessRuleError("Пользователь уже заблокирован")
        self._auth.set_status(user_id, "BLOCKED")
        with self._session_factory() as session:
            add_event(session, "UserBlocked", {"user_id": user_id, "admin_id": admin_id,
                                               "blocked_at": fmt_dt(utcnow())})
            session.commit()
        return {"user_id": user_id, "status": "BLOCKED"}
