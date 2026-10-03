from typing import Optional
from .base import NotFoundError, RequestClientBase

MOCK_REQUESTS = {
    "req-1": {
        "id": "req-1",
        "client_id": "user-1",
        "expert_id": None,
        "symptoms": "Пожелтение листьев, пятна",
        "ai_prediagnosis": "Возможно мучнистая роса",
        "status": "CREATED",
        "created_at": "2026-01-15T10:30:00Z",
        "completed_at": None,
        "photos": [
            {"id": "p-1", "url": "https://minio/req-1/photo1.jpg", "uploaded_at": "2026-01-15T10:30:00Z"},
            {"id": "p-2", "url": "https://minio/req-1/photo2.jpg", "uploaded_at": "2026-01-15T10:31:00Z"},
        ],
    },
    "req-2": {
        "id": "req-2",
        "client_id": "user-1",
        "expert_id": "user-2",
        "symptoms": "Белый налёт на листьях",
        "ai_prediagnosis": "Мучнистая роса",
        "status": "IN_PROGRESS",
        "created_at": "2026-01-16T11:00:00Z",
        "completed_at": None,
        "photos": [],
    },
    "req-3": {
        "id": "req-3",
        "client_id": "user-4",
        "expert_id": None,
        "symptoms": "Сохнут кончики листьев",
        "ai_prediagnosis": None,
        "status": "CREATED",
        "created_at": "2026-01-17T09:00:00Z",
        "completed_at": None,
        "photos": [],
    },
}

MOCK_DISEASES = {
    "dis-1": {
        "id": "dis-1",
        "name": "Мучнистая роса",
        "description": "Грибковое заболевание",
        "symptoms": "Белый налёт на листьях",
        "treatment": "Обработка фунгицидами",
    },
    "dis-2": {
        "id": "dis-2",
        "name": "Корневая гниль",
        "description": "Загнивание корней",
        "symptoms": "Пожелтение, увядание",
        "treatment": "Пересадка, дренаж",
    },
}


class MockRequestClient(RequestClientBase):
    #Mock-клиент Request Service

    def get_request(self, request_id: str) -> dict:
        req = MOCK_REQUESTS.get(request_id)
        if not req:
            raise NotFoundError(f"Заявка {request_id} не найдена")
        return req

    def list_requests(self, client_id: Optional[str] = None,
                      expert_id: Optional[str] = None,
                      status: Optional[str] = None) -> list[dict]:
        reqs = list(MOCK_REQUESTS.values())
        if client_id:
            reqs = [r for r in reqs if r["client_id"] == client_id]
        if expert_id:
            reqs = [r for r in reqs if r["expert_id"] == expert_id]
        if status:
            reqs = [r for r in reqs if r["status"] == status]
        return reqs

    def list_available_requests(self) -> list[dict]:
        return [r for r in MOCK_REQUESTS.values() if r["status"] == "CREATED"]

    def get_disease(self, disease_id: str) -> dict:
        disease = MOCK_DISEASES.get(disease_id)
        if not disease:
            raise NotFoundError(f"Болезнь {disease_id} не найдена")
        return disease