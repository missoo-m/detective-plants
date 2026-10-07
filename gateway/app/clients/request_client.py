import copy
import os
from typing import Optional

from ..errors import BusinessRuleError, NotFoundError, PermissionDeniedError, ValidationError
from .base import RequestClientBase
from .common import check_period, check_sort, count_by, lower_bound, new_id, now_iso, paginate, parse_iso, upper_bound

REQUEST_STATUSES = {"CREATED", "PENDING", "IN_PROGRESS", "DONE", "CANCELLED"}
ACTIVE_STATUSES = {"CREATED", "PENDING", "IN_PROGRESS"}
TRANSITIONS = {"CREATED": {"PENDING", "CANCELLED"}, "PENDING": {"IN_PROGRESS", "CANCELLED"},
               "IN_PROGRESS": {"DONE"}, "DONE": set(), "CANCELLED": set()}
MAX_ACTIVE, MAX_PHOTOS, MAX_FILE_BYTES = 3, 5, 5 * 1024 * 1024
AI_RULES = [("налёт", "Мучнистая роса"), ("гниль", "Корневая гниль"), ("пятна", "Пятнистость листьев")]

MOCK_REQUESTS = {
    "req-1": {"id": "req-1", "client_id": "user-1", "expert_id": None, "symptoms": "Пожелтение листьев, пятна",
              "ai_prediagnosis": "Возможно мучнистая роса", "status": "CREATED",
              "created_at": "2026-01-15T10:30:00Z", "completed_at": None,
              "photos": [{"id": "p-1", "url": "https://minio/req-1/photo1.jpg", "uploaded_at": "2026-01-15T10:30:00Z"},
                         {"id": "p-2", "url": "https://minio/req-1/photo2.jpg", "uploaded_at": "2026-01-15T10:31:00Z"}]},
    "req-2": {"id": "req-2", "client_id": "user-1", "expert_id": "user-2", "symptoms": "Белый налёт на листьях",
              "ai_prediagnosis": "Мучнистая роса", "status": "IN_PROGRESS",
              "created_at": "2026-01-16T11:00:00Z", "completed_at": None, "photos": []},
    "req-3": {"id": "req-3", "client_id": "user-4", "expert_id": None, "symptoms": "Сохнут кончики листьев",
              "ai_prediagnosis": None, "status": "CREATED", "created_at": "2026-01-17T09:00:00Z",
              "completed_at": None, "photos": []},
    "req-4": {"id": "req-4", "client_id": "user-4", "expert_id": "user-2", "symptoms": "Скручивание молодых листьев",
              "ai_prediagnosis": None, "status": "DONE", "created_at": "2026-01-05T09:00:00Z",
              "completed_at": "2026-01-12T18:00:00Z", "photos": []},
    "req-5": {"id": "req-5", "client_id": "user-1", "expert_id": None, "symptoms": "Вялость растения после пересадки",
              "ai_prediagnosis": None, "status": "CANCELLED", "created_at": "2026-01-03T14:00:00Z",
              "completed_at": "2026-01-03T15:00:00Z", "photos": []},
}

MOCK_DISEASES = {
    "dis-1": {"id": "dis-1", "name": "Мучнистая роса", "description": "Грибковое заболевание",
              "symptoms": "Белый налёт на листьях", "treatment": "Обработка фунгицидами"},
    "dis-2": {"id": "dis-2", "name": "Корневая гниль", "description": "Загнивание корней",
              "symptoms": "Пожелтение, увядание", "treatment": "Пересадка, дренаж"},
}


class MockRequestClient(RequestClientBase):
    #Mock Request Service

    def __init__(self):
        self.requests = copy.deepcopy(MOCK_REQUESTS)
        self.diseases = copy.deepcopy(MOCK_DISEASES)

    @staticmethod
    def _registry():
        from .. import clients
        return clients

    def _require_active(self, user_id: str, role: str) -> None:
        user = self._registry().auth_client.get_user(user_id)
        if user["status"] != "ACTIVE":
            raise PermissionDeniedError("Учётная запись пользователя заблокирована или не активна")
        if user["role"] != role:
            raise PermissionDeniedError(f"Действие доступно только роли {role}")

    @staticmethod
    def _change_status(req: dict, new_status: str) -> None:
        if new_status not in TRANSITIONS[req["status"]]:
            raise BusinessRuleError(f"Недопустимый переход статуса заявки: {req['status']} → {new_status}")
        req["status"] = new_status
        if new_status in ("DONE", "CANCELLED"):
            req["completed_at"] = now_iso()

    def get_request(self, request_id: str) -> dict:
        req = self.requests.get(request_id)
        if not req:
            raise NotFoundError(f"Заявка {request_id} не найдена")
        return req

    def list_requests(self, client_id=None, expert_id=None, statuses=None, search=None, created_from=None,
                      created_to=None, has_expert=None, sort_by="created_at", descending=False, limit=None,
                      offset=0) -> list[dict]:
        check_sort(sort_by, {"created_at", "status"})
        start, end = lower_bound(created_from), upper_bound(created_to)
        check_period(start, end)
        items = list(self.requests.values())
        if client_id:
            items = [r for r in items if r["client_id"] == client_id]
        if expert_id:
            items = [r for r in items if r["expert_id"] == expert_id]
        if statuses:
            items = [r for r in items if r["status"] in statuses]
        if search:
            items = [r for r in items if search.lower() in r["symptoms"].lower()]
        if start:
            items = [r for r in items if parse_iso(r["created_at"]) >= start]
        if end:
            items = [r for r in items if parse_iso(r["created_at"]) <= end]
        if has_expert is not None:
            items = [r for r in items if bool(r["expert_id"]) == has_expert]
        items.sort(key=lambda r: (r[sort_by], r["id"]), reverse=descending)
        return paginate(items, limit, offset)

    def list_available_requests(self, **kwargs) -> list[dict]:
        kwargs.pop("statuses", None)
        return self.list_requests(statuses=["CREATED"], **kwargs)

    def requests_summary(self, client_id=None, expert_id=None) -> dict:
        items = self.list_requests(client_id=client_id, expert_id=expert_id)
        return {"total": len(items), "by_status": count_by(items, "status")}

    def get_disease(self, disease_id: str) -> dict:
        disease = self.diseases.get(disease_id)
        if not disease:
            raise NotFoundError(f"Болезнь {disease_id} не найдена")
        return disease

    def create_request(self, client_id: str, symptoms: str, photo_urls: list) -> dict:
        symptoms = (symptoms or "").strip()
        if not 10 <= len(symptoms) <= 2000:
            raise ValidationError("Описание симптомов должно содержать от 10 до 2000 символов")
        if len(photo_urls) > MAX_PHOTOS:
            raise ValidationError(f"К заявке можно прикрепить не более {MAX_PHOTOS} фото")
        if any(not u.startswith(("http://", "https://")) for u in photo_urls):
            raise ValidationError("Ссылка на фото должна начинаться с http:// или https://")
        self._require_active(client_id, "CLIENT")
        active = [r for r in self.requests.values() if r["client_id"] == client_id and r["status"] in ACTIVE_STATUSES]
        if len(active) >= MAX_ACTIVE:
            raise BusinessRuleError(f"Нельзя иметь более {MAX_ACTIVE} активных заявок одновременно")
        ai = next((d for key, d in AI_RULES if key in symptoms.lower()), None)
        request_id, stamp = new_id("req"), now_iso()
        self.requests[request_id] = {
            "id": request_id, "client_id": client_id, "expert_id": None, "symptoms": symptoms,
            "ai_prediagnosis": ai, "status": "CREATED", "created_at": stamp, "completed_at": None,
            "photos": [{"id": new_id("p"), "url": u, "uploaded_at": stamp} for u in photo_urls]}
        return self.requests[request_id]

    def add_photo(self, request_id: str, client_id: str, file_name: str, content: bytes) -> dict:
        if os.path.splitext(file_name or "")[1].lower() not in {".jpg", ".jpeg", ".png"}:
            raise ValidationError("Допустимы только файлы JPG и PNG")
        if not content:
            raise ValidationError("Файл пуст")
        if len(content) > MAX_FILE_BYTES:
            raise ValidationError("Размер файла не должен превышать 5 МБ")
        req = self.get_request(request_id)
        if req["client_id"] != client_id:
            raise PermissionDeniedError("Добавлять фото может только автор заявки")
        if req["status"] not in ("CREATED", "PENDING"):
            raise BusinessRuleError("Фото можно добавлять только до начала работы эксперта")
        if len(req["photos"]) >= MAX_PHOTOS:
            raise BusinessRuleError(f"К заявке уже прикреплено {MAX_PHOTOS} фото")
        photo = {"id": new_id("p"), "url": f"https://minio/{request_id}/{new_id('f')}-{file_name}",
                 "uploaded_at": now_iso()}
        req["photos"].append(photo)
        return photo

    def select_expert(self, request_id: str, client_id: str, expert_id: str) -> dict:
        req = self.get_request(request_id)
        if req["client_id"] != client_id:
            raise PermissionDeniedError("Выбрать эксперта может только автор заявки")
        if req["status"] != "CREATED":
            raise BusinessRuleError(f"Эксперта можно выбрать только для новой заявки, сейчас статус {req['status']}")
        self._require_active(expert_id, "EXPERT")
        registry = self._registry()
        if not registry.expert_client.has_responded(request_id, expert_id):
            raise BusinessRuleError("Этот эксперт не откликался на заявку")
        req["expert_id"] = expert_id
        self._change_status(req, "PENDING")
        registry.expert_client.accept_response(request_id, expert_id)
        return req

    def cancel_request(self, request_id: str, client_id: str) -> dict:
        req = self.get_request(request_id)
        if req["client_id"] != client_id:
            raise PermissionDeniedError("Отменить заявку может только её автор")
        if req["status"] not in ("CREATED", "PENDING"):
            raise BusinessRuleError(
                f"Заявку в статусе {req['status']} отменить нельзя: отмена возможна до начала работы эксперта")
        self._change_status(req, "CANCELLED")
        return req

    def start_work(self, request_id: str) -> dict:
        req = self.get_request(request_id)
        self._change_status(req, "IN_PROGRESS")
        return req

    def complete_request(self, request_id: str) -> dict:
        req = self.get_request(request_id)
        self._change_status(req, "DONE")
        return req
