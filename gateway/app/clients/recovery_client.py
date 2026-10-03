from typing import Optional
from .base import NotFoundError, RecoveryClientBase

MOCK_TRACKERS = {
    "req-2": {
        "id": "track-1",
        "request_id": "req-2",
        "client_id": "user-1",
        "expert_id": "user-2",
        "start_date": "2026-01-16T12:00:00Z",
        "end_date": "2026-01-30T12:00:00Z",
        "status": "ACTIVE",
        "current_stage": "START",
        "history": [
            {"id": "h-1", "record_type": "TREATMENT_UPDATE",
             "date": "2026-01-17T10:00:00Z",
             "photo_url": None,
             "change_description": "Начало лечения",
             "author_id": "user-2"},
            {"id": "h-2", "record_type": "PHOTO",
             "date": "2026-01-18T09:00:00Z",
             "photo_url": "https://minio/track-1/photo1.jpg",
             "change_description": None,
             "author_id": "user-1"},
        ],
    },
}


class MockRecoveryClient(RecoveryClientBase):
    #Mock-клиент Recovery Service

    def get_tracker(self, tracker_id: str) -> dict:
        for t in MOCK_TRACKERS.values():
            if t["id"] == tracker_id:
                return t
        raise NotFoundError(f"Трекер {tracker_id} не найден")

    def get_tracker_by_request(self, request_id: str) -> Optional[dict]:
        return MOCK_TRACKERS.get(request_id)
