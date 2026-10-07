from datetime import datetime
from typing import Callable, Optional

from sqlalchemy.orm import Session

from .clients import AuthClient, MockAuthClient
from .database import get_session_factory
from .errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from .models import ExpertApplication, utcnow
from .repository import ApplicationRepository
from .schemas import ApplicationDTO, ApplicationsSummaryDTO
from .utils import fmt_dt, parse_uuid

APPLICATION_STATUSES = {"PENDING", "APPROVED", "REJECTED"}


def _dto(a: ExpertApplication) -> ApplicationDTO:
    return ApplicationDTO(id=str(a.id), user_id=str(a.user_id), documents_url=a.documents_url, status=a.status,
                          submitted_at=fmt_dt(a.submitted_at), verified_at=fmt_dt(a.verified_at))


class AdminService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None, auth: Optional[AuthClient] = None):
        self._session_factory = session_factory or get_session_factory()
        self._auth = auth or MockAuthClient()

    def _require_admin(self, admin_id: str) -> None:
        user = self._auth.get_user(admin_id)
        if user["status"] != "ACTIVE" or user["role"] != "ADMIN":
            raise PermissionDeniedError("Действие доступно только администратору")

    # чтение
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

    # бизнес-операции
    def submit_application(self, user_id: str, documents_url: str) -> ApplicationDTO:
        url = (documents_url or "").strip()
        if not url.startswith(("http://", "https://")) or len(url) > 500:
            raise InvalidValueError("documents_url должен быть ссылкой http(s) длиной до 500 символов")
        uid = parse_uuid(user_id)
        user = self._auth.get_user(user_id)
        if user["status"] != "ACTIVE":
            raise PermissionDeniedError("Учётная запись пользователя заблокирована или не активна")
        if user["role"] != "CLIENT":
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

    def verify_expert(self, application_id: str, admin_id: str, approve: bool) -> ApplicationDTO:
        self._require_admin(admin_id)
        with self._session_factory() as session:
            app = ApplicationRepository(session).get_by_id(parse_uuid(application_id))
            if app is None:
                raise NotFoundError(f"Заявка эксперта {application_id} не найдена")
            if app.status != "PENDING":
                raise BusinessRuleError(f"Заявка уже рассмотрена (статус {app.status})")
            app.status = "APPROVED" if approve else "REJECTED"
            app.verified_at = utcnow()
            session.commit()
            result, user_id = _dto(app), str(app.user_id)
        if approve:
            self._auth.assign_role(user_id, "EXPERT")
        return result

    def block_user(self, admin_id: str, user_id: str) -> dict:
        self._require_admin(admin_id)
        parse_uuid(user_id)
        target = self._auth.get_user(user_id)
        if target["role"] == "ADMIN":
            raise BusinessRuleError("Администратора заблокировать нельзя")
        if target["status"] == "BLOCKED":
            raise BusinessRuleError("Пользователь уже заблокирован")
        self._auth.set_status(user_id, "BLOCKED")
        return {"user_id": user_id, "status": "BLOCKED"}
