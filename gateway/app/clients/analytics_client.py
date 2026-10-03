from .base import AnalyticsClientBase, NotFoundError

MOCK_EXPERT_STATS = {
    "user-2": {"expert_id": "user-2", "total_requests": 2,
               "completed_requests": 1, "avg_rating": 4.8},
}

MOCK_DISEASE_STATS = [
    {"disease_id": "dis-1", "count": 3, "period": "2026-01"},
    {"disease_id": "dis-2", "count": 1, "period": "2026-01"},
    {"disease_id": "dis-1", "count": 1, "period": "2025-12"},
]


class MockAnalyticsClient(AnalyticsClientBase):
    #Mock-клиент Analytics Service

    def get_expert_stats(self, expert_id: str) -> dict:
        stats = MOCK_EXPERT_STATS.get(expert_id)
        if not stats:
            raise NotFoundError(f"Статистика эксперта {expert_id} не найдена")
        return stats

    def list_disease_stats(self, period: str) -> list[dict]:
        return [s for s in MOCK_DISEASE_STATS if s["period"] == period]
