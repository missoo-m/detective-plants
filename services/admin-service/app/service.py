from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .errors import InvalidValueError, NotFoundError
from .models import ExpertApplication
from .repository import ApplicationRepository
from .schemas import ApplicationDTO
from .utils import fmt_dt, parse_uuid

APPLICATION_STATUSES = {"PENDING", "APPROVED", "REJECTED"}


def _dto(a: ExpertApplication) -> ApplicationDTO:
    return ApplicationDTO(id=str(a.id), user_id=str(a.user_id), documents_url=a.documents_url,
                          status=a.status, submitted_at=fmt_dt(a.submitted_at),
                          verified_at=fmt_dt(a.verified_at))


class AdminService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    def get_application(self, application_id: str) -> ApplicationDTO:
        aid = parse_uuid(application_id)
        with self._session_factory() as session:
            app = ApplicationRepository(session).get_by_id(aid)
            if app is None:
                raise NotFoundError(f"Заявка эксперта {application_id} не найдена")
            return _dto(app)

    def list_applications(self, status: Optional[str] = None) -> list[ApplicationDTO]:
        if status is not None and status not in APPLICATION_STATUSES:
            raise InvalidValueError(f"Неизвестный статус заявки эксперта: {status}")
        with self._session_factory() as session:
            return [_dto(a) for a in ApplicationRepository(session).list_applications(status)]
