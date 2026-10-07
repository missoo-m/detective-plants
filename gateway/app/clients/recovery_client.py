import copy
import os
from datetime import timedelta
from typing import Optional

from ..errors import BusinessRuleError, NotFoundError, PermissionDeniedError, ValidationError
from .base import RecoveryClientBase
from .common import new_id, now_iso, parse_iso

MAX_FILE_BYTES = 5 * 1024 * 1024

MOCK_TRACKERS = {
    "req-2": {
        "id": "track-1", "request_id": "req-2", "client_id": "user-1", "expert_id": "user-2",
        "start_date": "2026-01-16T12:00:00Z", "end_date": "2026-01-30T12:00:00Z", "status": "ACTIVE",
        "current_stage": "START",
        "history": [
            {"id": "h-1", "record_type": "TREATMENT_UPDATE", "date": "2026-01-17T10:00:00Z", "photo_url": None,
             "change_description": "Начало лечения", "author_id": "user-2"},
            {"id": "h-2", "record_type": "PHOTO", "date": "2026-01-18T09:00:00Z",
             "photo_url": "https://minio/track-1/photo1.jpg", "change_description": None, "author_id": "user-1"},
        ],
    },
}


class MockRecoveryClient(RecoveryClientBase):
    #Mock Recovery Service

    def __init__(self):
        self.trackers = copy.deepcopy(MOCK_TRACKERS)       

    @staticmethod
    def _registry():
        from .. import clients
        return clients

    def _find(self, tracker_id: str) -> dict:
        for t in self.trackers.values():
            if t["id"] == tracker_id:
                return t
        raise NotFoundError(f"Трекер {tracker_id} не найден")

    @staticmethod
    def _require_active(tracker: dict) -> None:
        if tracker["status"] != "ACTIVE":
            raise BusinessRuleError(f"Трекер уже в статусе {tracker['status']}, изменять его нельзя")

    def get_tracker(self, tracker_id: str) -> dict:
        return self._find(tracker_id)

    def get_tracker_by_request(self, request_id: str) -> Optional[dict]:
        return self.trackers.get(request_id)

    def tracker_progress(self, tracker_id: str) -> dict:
        t = self._find(tracker_id)
        start, end = parse_iso(t["start_date"]), parse_iso(t["end_date"])
        total = max((end - start).days, 1)
        elapsed = min(max((parse_iso(now_iso()) - start).days, 0), total)
        if t["status"] == "COMPLETED":
            elapsed = total
        return {"tracker_id": t["id"], "total_days": total, "elapsed_days": elapsed,
                "percent": round(elapsed * 100 / total, 1),
                "photos_count": sum(1 for h in t["history"] if h["record_type"] == "PHOTO"),
                "updates_count": sum(1 for h in t["history"] if h["record_type"] == "TREATMENT_UPDATE")}

    def create_tracker(self, request_id: str, client_id: str, expert_id: str, duration_days: int) -> dict:
        if not 1 <= duration_days <= 60:
            raise ValidationError("Длительность трекера должна быть от 1 до 60 дней")
        if request_id in self.trackers:
            raise BusinessRuleError("Для этой заявки трекер уже создан")
        start = parse_iso(now_iso())
        tracker = {"id": new_id("track"), "request_id": request_id, "client_id": client_id, "expert_id": expert_id,
                   "start_date": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "end_date": (start + timedelta(days=duration_days)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "status": "ACTIVE", "current_stage": "START", "history": []}
        self.trackers[request_id] = tracker
        return tracker

    def upload_photo(self, tracker_id: str, author_id: str, file_name: str, content: bytes) -> dict:
        if os.path.splitext(file_name or "")[1].lower() not in {".jpg", ".jpeg", ".png"}:
            raise ValidationError("Допустимы только файлы JPG и PNG")
        if not content:
            raise ValidationError("Файл пуст")
        if len(content) > MAX_FILE_BYTES:
            raise ValidationError("Размер файла не должен превышать 5 МБ")
        t = self._find(tracker_id)
        if t["client_id"] != author_id:
            raise PermissionDeniedError("Загружать фото в трекер может только клиент — владелец заявки")
        self._require_active(t)
        record = {"id": new_id("h"), "record_type": "PHOTO", "date": now_iso(), "change_description": None,
                  "photo_url": f"https://minio/{tracker_id}/{new_id('f')}-{file_name}", "author_id": author_id}
        t["history"].append(record)
        self._registry().notification_client.create_notification(
            t["expert_id"], "TRACKER_PHOTO", "Клиент загрузил новое фото растения в трекер")
        return record

    def update_treatment(self, tracker_id: str, expert_id: str, change_description: str,
                         new_stage: Optional[str]) -> dict:
        text = (change_description or "").strip()
        if not 3 <= len(text) <= 2000:
            raise ValidationError("Описание корректировки должно содержать от 3 до 2000 символов")
        if new_stage is not None and not 1 <= len(new_stage.strip()) <= 100:
            raise ValidationError("Название этапа должно содержать от 1 до 100 символов")
        t = self._find(tracker_id)
        if t["expert_id"] != expert_id:
            raise PermissionDeniedError("Корректировать лечение может только эксперт, ведущий заявку")
        self._require_active(t)
        record = {"id": new_id("h"), "record_type": "TREATMENT_UPDATE", "date": now_iso(), "photo_url": None,
                  "change_description": text, "author_id": expert_id}
        t["history"].append(record)
        if new_stage is not None:
            t["current_stage"] = new_stage.strip()
        self._registry().notification_client.create_notification(
            t["client_id"], "TREATMENT_UPDATED", "Эксперт скорректировал план лечения")
        return record

    def complete_tracker(self, tracker_id: str, expert_id: str) -> dict:
        t = self._find(tracker_id)
        if t["expert_id"] != expert_id:
            raise PermissionDeniedError("Завершить трекер может только эксперт, ведущий заявку")
        self._require_active(t)
        t["status"], t["end_date"], t["current_stage"] = "COMPLETED", now_iso(), "COMPLETED"
        self._registry().request_client.complete_request(t["request_id"])
        return t
