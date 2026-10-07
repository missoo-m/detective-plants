import copy
from typing import Optional

from ..errors import BusinessRuleError, NotFoundError, PermissionDeniedError, ValidationError
from .base import ExpertClientBase
from .common import count_by, new_id, now_iso

MAX_STEPS = 20

MOCK_RESPONSES = [
    {"id": "resp-1", "request_id": "req-1", "expert_id": "user-2", "comment": "Готов взять заявку, похоже на мучнистую росу",
     "status": "PENDING", "created_at": "2026-01-15T11:00:00Z"},
    {"id": "resp-2", "request_id": "req-2", "expert_id": "user-2", "comment": "Беру в работу",
     "status": "ACCEPTED", "created_at": "2026-01-16T11:30:00Z"},
]

MOCK_DIAGNOSES = {
    "diag-1": {"id": "diag-1", "request_id": "req-2", "expert_id": "user-2", "disease_id": "dis-1",
               "description": "Мучнистая роса на листьях томата", "ai_prediagnosis": "Мучнистая роса",
               "duration_days": 14, "created_at": "2026-01-16T12:00:00Z",
               "checklist": [{"id": "step-1", "step": "Удалить поражённые листья", "frequency": "однократно",
                              "duration_days": 1},
                             {"id": "step-2", "step": "Обработать фунгицидом", "frequency": "раз в 5 дней",
                              "duration_days": 14}]},
}


def _clean_step(step: dict) -> dict:
    text = (step.get("step") or "").strip()
    if not 3 <= len(text) <= 500:
        raise ValidationError("Шаг лечения должен содержать от 3 до 500 символов")
    days = step.get("duration_days")
    if days is not None and not 1 <= days <= 60:
        raise ValidationError("Длительность шага должна быть от 1 до 60 дней")
    return {"id": new_id("step"), "step": text, "frequency": step.get("frequency"), "duration_days": days}


class MockExpertClient(ExpertClientBase):
    #Mock Expert Service

    def __init__(self):
        self.responses = copy.deepcopy(MOCK_RESPONSES)
        self.diagnoses = copy.deepcopy(MOCK_DIAGNOSES)

    @staticmethod
    def _registry():
        from .. import clients
        return clients

    def _require_expert(self, expert_id: str) -> None:
        user = self._registry().auth_client.get_user(expert_id)
        if user["status"] != "ACTIVE":
            raise PermissionDeniedError("Учётная запись пользователя заблокирована или не активна")
        if user["role"] != "EXPERT":
            raise PermissionDeniedError("Действие доступно только эксперту")

    # ---- чтение
    def list_responses(self, request_id: str) -> list[dict]:
        return [r for r in self.responses if r["request_id"] == request_id]

    def has_responded(self, request_id: str, expert_id: str) -> bool:
        return any(r["request_id"] == request_id and r["expert_id"] == expert_id for r in self.responses)

    def responses_summary(self, expert_id: str) -> dict:
        own = [r for r in self.responses if r["expert_id"] == expert_id]
        return {"total": len(own), "by_status": count_by(own, "status")}

    def get_diagnosis(self, diagnosis_id: str) -> dict:
        diagnosis = self.diagnoses.get(diagnosis_id)
        if not diagnosis:
            raise NotFoundError(f"Диагноз {diagnosis_id} не найден")
        return diagnosis

    def get_diagnosis_by_request(self, request_id: str) -> dict:
        for d in self.diagnoses.values():
            if d["request_id"] == request_id:
                return d
        raise NotFoundError(f"Для заявки {request_id} диагноз ещё не поставлен")

    def respond_to_request(self, request_id: str, expert_id: str, comment: Optional[str]) -> dict:
        comment = (comment or "").strip() or None
        if comment and len(comment) > 500:
            raise ValidationError("Комментарий не должен превышать 500 символов")
        self._require_expert(expert_id)
        request = self._registry().request_client.get_request(request_id)
        if request["status"] != "CREATED":
            raise BusinessRuleError(f"Откликнуться можно только на новую заявку, сейчас статус {request['status']}")
        if self.has_responded(request_id, expert_id):
            raise BusinessRuleError("Вы уже откликнулись на эту заявку")
        response = {"id": new_id("resp"), "request_id": request_id, "expert_id": expert_id, "comment": comment,
                    "status": "PENDING", "created_at": now_iso()}
        self.responses.append(response)
        return response

    def accept_response(self, request_id: str, expert_id: str) -> None:
        mine = self.list_responses(request_id)
        if not any(r["expert_id"] == expert_id for r in mine):
            raise BusinessRuleError("Эксперт не откликался на эту заявку")
        for r in mine:
            r["status"] = "ACCEPTED" if r["expert_id"] == expert_id else "REJECTED"

    def create_diagnosis(self, request_id, expert_id, disease_id, description, duration_days, checklist) -> dict:
        description = (description or "").strip()
        if not 5 <= len(description) <= 2000:
            raise ValidationError("Описание диагноза должно содержать от 5 до 2000 символов")
        if not 1 <= duration_days <= 60:
            raise ValidationError("Длительность лечения должна быть от 1 до 60 дней")
        steps = [_clean_step(s) for s in checklist]
        if len(steps) > MAX_STEPS:
            raise ValidationError(f"В чек-листе может быть не более {MAX_STEPS} шагов")
        self._require_expert(expert_id)
        registry = self._registry()
        request = registry.request_client.get_request(request_id)
        if request["expert_id"] != expert_id:
            raise PermissionDeniedError("Диагноз может поставить только эксперт, выбранный клиентом")
        if request["status"] != "IN_PROGRESS":
            raise BusinessRuleError("Диагноз можно поставить только по оплаченной заявке в работе")
        registry.request_client.get_disease(disease_id)
        if any(d["request_id"] == request_id for d in self.diagnoses.values()):
            raise BusinessRuleError("Диагноз по этой заявке уже поставлен")
        diagnosis = {"id": new_id("diag"), "request_id": request_id, "expert_id": expert_id, "disease_id": disease_id,
                     "description": description, "ai_prediagnosis": request.get("ai_prediagnosis"),
                     "duration_days": duration_days, "created_at": now_iso(), "checklist": steps}
        self.diagnoses[diagnosis["id"]] = diagnosis
        registry.recovery_client.create_tracker(request_id, request["client_id"], expert_id, duration_days)
        return diagnosis

    def add_treatment_step(self, diagnosis_id, expert_id, step, frequency, duration_days) -> dict:
        data = _clean_step({"step": step, "frequency": frequency, "duration_days": duration_days})
        diagnosis = self.get_diagnosis(diagnosis_id)
        if diagnosis["expert_id"] != expert_id:
            raise PermissionDeniedError("Изменять чек-лист может только автор диагноза")
        if len(diagnosis["checklist"]) >= MAX_STEPS:
            raise BusinessRuleError(f"В чек-листе уже {MAX_STEPS} шагов")
        diagnosis["checklist"].append(data)
        return data
