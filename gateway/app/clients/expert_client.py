from .base import ExpertClientBase, NotFoundError

MOCK_RESPONSES = [
    {"id": "resp-1", "request_id": "req-1", "expert_id": "user-2",
     "comment": "Готов взять заявку, похоже на мучнистую росу",
     "status": "PENDING", "created_at": "2026-01-15T11:00:00Z"},
    {"id": "resp-2", "request_id": "req-2", "expert_id": "user-2",
     "comment": "Беру в работу", "status": "ACCEPTED",
     "created_at": "2026-01-16T11:30:00Z"},
]

MOCK_DIAGNOSES = {
    "diag-1": {
        "id": "diag-1", "request_id": "req-2", "expert_id": "user-2", "disease_id": "dis-1",
        "description": "Мучнистая роса на листьях томата",
        "ai_prediagnosis": "Мучнистая роса", "duration_days": 14,
        "created_at": "2026-01-16T12:00:00Z",
        "checklist": [
            {"id": "step-1", "step": "Удалить поражённые листья",
             "frequency": "однократно", "duration_days": 1},
            {"id": "step-2", "step": "Обработать фунгицидом",
             "frequency": "раз в 5 дней", "duration_days": 14},
        ],
    },
}


class MockExpertClient(ExpertClientBase):
    #Mock-клиент Expert Service

    def list_responses(self, request_id: str) -> list[dict]:
        return [r for r in MOCK_RESPONSES if r["request_id"] == request_id]

    def get_diagnosis(self, diagnosis_id: str) -> dict:
        diagnosis = MOCK_DIAGNOSES.get(diagnosis_id)
        if not diagnosis:
            raise NotFoundError(f"Диагноз {diagnosis_id} не найден")
        return diagnosis

    def get_diagnosis_by_request(self, request_id: str) -> dict:
        for d in MOCK_DIAGNOSES.values():
            if d["request_id"] == request_id:
                return d
        raise NotFoundError(f"Для заявки {request_id} диагноз ещё не поставлен")
