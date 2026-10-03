from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .errors import InvalidValueError, NotFoundError
from .models import RecoveryTracker
from .repository import TrackerRepository
from .schemas import HistoryDTO, TrackerDTO
from .utils import fmt_dt, parse_uuid

TRACKER_STATUSES = {"ACTIVE", "COMPLETED", "CANCELLED"}


def _to_dto(t: RecoveryTracker) -> TrackerDTO:
    return TrackerDTO(
        id=str(t.id), request_id=str(t.request_id), client_id=str(t.client_id),
        expert_id=str(t.expert_id), start_date=fmt_dt(t.start_date), end_date=fmt_dt(t.end_date),
        status=t.status, current_stage=t.current_stage,
        history=[HistoryDTO(id=str(h.id), record_type=h.record_type, date=fmt_dt(h.date),
                            photo_url=h.photo_url, change_description=h.change_description,
                            author_id=str(h.author_id)) for h in t.history],
    )


class RecoveryService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    def get_tracker(self, tracker_id: str) -> TrackerDTO:
        tid = parse_uuid(tracker_id)
        with self._session_factory() as session:
            tracker = TrackerRepository(session).get_by_id(tid)
            if tracker is None:
                raise NotFoundError(f"Трекер {tracker_id} не найден")
            return _to_dto(tracker)

    def get_tracker_by_request(self, request_id: str) -> TrackerDTO:
        rid = parse_uuid(request_id)
        with self._session_factory() as session:
            tracker = TrackerRepository(session).get_by_request(rid)
            if tracker is None:
                raise NotFoundError(f"Для заявки {request_id} трекер не создан")
            return _to_dto(tracker)

    def list_trackers(self, client_id: Optional[str] = None, expert_id: Optional[str] = None,
                      status: Optional[str] = None) -> list[TrackerDTO]:
        if status is not None and status not in TRACKER_STATUSES:
            raise InvalidValueError(f"Неизвестный статус трекера: {status}")
        cid = parse_uuid(client_id) if client_id else None
        eid = parse_uuid(expert_id) if expert_id else None
        with self._session_factory() as session:
            return [_to_dto(t) for t in TrackerRepository(session).list_trackers(cid, eid, status)]
