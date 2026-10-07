import copy
from typing import Optional

from ..errors import NotFoundError
from .base import AnalyticsClientBase
from .common import check_sort, paginate

MOCK_EXPERT_STATS = {
    "user-2": {"expert_id": "user-2", "total_requests": 2, "completed_requests": 1, "avg_rating": 4.8},
    "user-6": {"expert_id": "user-6", "total_requests": 10, "completed_requests": 8, "avg_rating": 4.2},
}

MOCK_DISEASE_STATS = [
    {"disease_id": "dis-1", "count": 3, "period": "2026-01"},
    {"disease_id": "dis-2", "count": 1, "period": "2026-01"},
    {"disease_id": "dis-1", "count": 1, "period": "2025-12"},
]


class MockAnalyticsClient(AnalyticsClientBase):
    #Mock Analytics Service

    def __init__(self):
        self.expert_stats = copy.deepcopy(MOCK_EXPERT_STATS)
        self.disease_stats = copy.deepcopy(MOCK_DISEASE_STATS)

    def get_expert_stats(self, expert_id: str) -> dict:
        stats = self.expert_stats.get(expert_id)
        if not stats:
            raise NotFoundError(f"Статистика эксперта {expert_id} не найдена")
        return stats

    def top_experts(self, sort_by="completed_requests", descending=True, limit=5) -> list[dict]:
        check_sort(sort_by, {"total_requests", "completed_requests", "avg_rating"})
        items = sorted(self.expert_stats.values(), key=lambda s: (s[sort_by], s["expert_id"]), reverse=descending)
        return paginate(items, limit, 0)

    def list_disease_stats(self, period: str, descending=True, limit=None) -> list[dict]:
        items = [s for s in self.disease_stats if s["period"] == period]
        items.sort(key=lambda s: (s["count"], s["disease_id"]), reverse=descending)
        return paginate(items, limit, 0)

    def platform_summary(self) -> dict:
        stats = list(self.expert_stats.values())
        total = sum(s["total_requests"] for s in stats)
        done = sum(s["completed_requests"] for s in stats)
        rating = sum(s["avg_rating"] * s["completed_requests"] for s in stats) / done if done else 0.0
        return {"experts": len(stats), "total_requests": total, "completed_requests": done,
                "completion_rate": round(done * 100 / total, 1) if total else 0.0, "avg_rating": round(rating, 2)}
