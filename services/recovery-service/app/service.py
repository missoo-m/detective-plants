import os
from datetime import datetime, timedelta
from typing import Callable, Optional

from sqlalchemy.orm import Session

from .clients import MockNotificationClient, MockRequestClient, MockStorageClient, \
    NotificationClient, RequestClient, StorageClient
from .database import get_session_factory
from .errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from .models import RecoveryTracker, TreatmentHistory, utcnow
from .repository import SORT_COLUMNS, TrackerRepository
from .schemas import HistoryDTO, ProgressDTO, TrackerDTO
from .utils import fmt_dt, parse_uuid

TRACKER_STATUSES = {"ACTIVE", "COMPLETED", "CANCELLED"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_BYTES = 5 * 1024 * 1024


def _to_dto(t: RecoveryTracker) -> TrackerDTO:
    return TrackerDTO(
        id=str(t.id), request_id=str(t.request_id), client_id=str(t.client_id), expert_id=str(t.expert_id),
        start_date=fmt_dt(t.start_date), end_date=fmt_dt(t.end_date), status=t.status, current_stage=t.current_stage,
        history=[_history(h) for h in t.history])


def _history(h: TreatmentHistory) -> HistoryDTO:
    return HistoryDTO(id=str(h.id), record_type=h.record_type, date=fmt_dt(h.date), photo_url=h.photo_url,
                      change_description=h.change_description, author_id=str(h.author_id))


class RecoveryService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None,
                 requests: Optional[RequestClient] = None, notifications: Optional[NotificationClient] = None,
                 storage: Optional[StorageClient] = None):
        self._session_factory = session_factory or get_session_factory()
        self._requests = requests or MockRequestClient()
        self._notifications = notifications or MockNotificationClient()
        self._storage = storage or MockStorageClient()

    @staticmethod
    def _load(repo: TrackerRepository, tracker_id: str) -> RecoveryTracker:
        tracker = repo.get_by_id(parse_uuid(tracker_id))
        if tracker is None:
            raise NotFoundError(f"Трекер {tracker_id} не найден")
        return tracker

    @staticmethod
    def _require_active(tracker: RecoveryTracker) -> None:
        if tracker.status != "ACTIVE":
            raise BusinessRuleError(f"Трекер уже в статусе {tracker.status}, изменять его нельзя")

    def get_tracker(self, tracker_id: str) -> TrackerDTO:
        with self._session_factory() as session:
            return _to_dto(self._load(TrackerRepository(session), tracker_id))

    def get_tracker_by_request(self, request_id: str) -> TrackerDTO:
        rid = parse_uuid(request_id)
        with self._session_factory() as session:
            tracker = TrackerRepository(session).get_by_request(rid)
            if tracker is None:
                raise NotFoundError(f"Для заявки {request_id} трекер не создан")
            return _to_dto(tracker)

    def list_trackers(self, client_id: Optional[str] = None, expert_id: Optional[str] = None,
                      status: Optional[str] = None, sort_by: str = "start_date",
                      descending: bool = False) -> list[TrackerDTO]:
        if status is not None and status not in TRACKER_STATUSES:
            raise InvalidValueError(f"Неизвестный статус трекера: {status}")
        if sort_by not in SORT_COLUMNS:
            raise InvalidValueError(f"Сортировка по полю {sort_by} не поддерживается")
        cid = parse_uuid(client_id) if client_id else None
        eid = parse_uuid(expert_id) if expert_id else None
        with self._session_factory() as session:
            return [_to_dto(t) for t in TrackerRepository(session).list_trackers(cid, eid, status, sort_by, descending)]

    def tracker_progress(self, tracker_id: str, now: Optional[datetime] = None) -> ProgressDTO:
        with self._session_factory() as session:
            t = self._load(TrackerRepository(session), tracker_id)
            end = t.end_date or t.start_date
            total = max((end - t.start_date).days, 1)
            current = now or utcnow()
            elapsed = min(max((current - t.start_date).days, 0), total)
            if t.status == "COMPLETED":
                elapsed = total
            return ProgressDTO(
                tracker_id=str(t.id), total_days=total, elapsed_days=elapsed, percent=round(elapsed * 100 / total, 1),
                photos_count=sum(1 for h in t.history if h.record_type == "PHOTO"),
                updates_count=sum(1 for h in t.history if h.record_type == "TREATMENT_UPDATE"))

    def create_tracker(self, request_id: str, client_id: str, expert_id: str, duration_days: int = 14) -> TrackerDTO:
        rid, cid, eid = parse_uuid(request_id), parse_uuid(client_id), parse_uuid(expert_id)
        if not 1 <= duration_days <= 60:
            raise InvalidValueError("Длительность трекера должна быть от 1 до 60 дней")
        with self._session_factory() as session:
            repo = TrackerRepository(session)
            if repo.get_by_request(rid) is not None:
                raise BusinessRuleError("Для этой заявки трекер уже создан")
            start = utcnow()
            tracker = RecoveryTracker(request_id=rid, client_id=cid, expert_id=eid, start_date=start,
                                      end_date=start + timedelta(days=duration_days), status="ACTIVE",
                                      current_stage="START")
            repo.add(tracker)
            session.commit()
            return _to_dto(tracker)

    def upload_photo(self, tracker_id: str, author_id: str, file_name: str, content: bytes) -> HistoryDTO:
        ext = os.path.splitext(file_name or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise InvalidValueError("Допустимы только файлы JPG и PNG")
        if not content:
            raise InvalidValueError("Файл пуст")
        if len(content) > MAX_FILE_BYTES:
            raise InvalidValueError("Размер файла не должен превышать 5 МБ")
        with self._session_factory() as session:
            tracker = self._load(TrackerRepository(session), tracker_id)
            if str(tracker.client_id) != author_id:
                raise PermissionDeniedError("Загружать фото в трекер может только клиент — владелец заявки")
            self._require_active(tracker)
            record = TreatmentHistory(tracker_id=tracker.id, record_type="PHOTO", author_id=tracker.client_id,
                                      photo_url=self._storage.save(str(tracker.id), file_name, content))
            session.add(record)
            session.commit()
            expert_id = str(tracker.expert_id)
            result = _history(record)
        self._notifications.send(expert_id, "TRACKER_PHOTO", "Клиент загрузил новое фото растения в трекер")
        return result

    def update_treatment(self, tracker_id: str, expert_id: str, change_description: str,
                         new_stage: Optional[str] = None) -> HistoryDTO:
        text = (change_description or "").strip()
        if not 3 <= len(text) <= 2000:
            raise InvalidValueError("Описание корректировки должно содержать от 3 до 2000 символов")
        if new_stage is not None and not 1 <= len(new_stage.strip()) <= 100:
            raise InvalidValueError("Название этапа должно содержать от 1 до 100 символов")
        with self._session_factory() as session:
            tracker = self._load(TrackerRepository(session), tracker_id)
            if str(tracker.expert_id) != expert_id:
                raise PermissionDeniedError("Корректировать лечение может только эксперт, ведущий заявку")
            self._require_active(tracker)
            record = TreatmentHistory(tracker_id=tracker.id, record_type="TREATMENT_UPDATE",
                                      author_id=tracker.expert_id, change_description=text)
            if new_stage is not None:
                tracker.current_stage = new_stage.strip()
            session.add(record)
            session.commit()
            client_id = str(tracker.client_id)
            result = _history(record)
        self._notifications.send(client_id, "TREATMENT_UPDATED", "Эксперт скорректировал план лечения")
        return result

    def complete_tracker(self, tracker_id: str, expert_id: str) -> TrackerDTO:
        with self._session_factory() as session:
            tracker = self._load(TrackerRepository(session), tracker_id)
            if str(tracker.expert_id) != expert_id:
                raise PermissionDeniedError("Завершить трекер может только эксперт, ведущий заявку")
            self._require_active(tracker)
            tracker.status = "COMPLETED"
            tracker.end_date = utcnow()
            tracker.current_stage = "COMPLETED"
            session.commit()
            result = _to_dto(tracker)
            request_id = str(tracker.request_id)
        self._requests.complete_request(request_id)
        return result
