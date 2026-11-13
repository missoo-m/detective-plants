import dataclasses
from typing import Callable, Optional

from sqlalchemy.orm import Session

from .cache import Cache, get_cache
from .database import get_session_factory
from .errors import InvalidValueError, NotFoundError
from .repository import EXPERT_SORT, StatsRepository
from .schemas import DiseaseStatsDTO, EventCounterDTO, ExpertStatsDTO, PlatformSummaryDTO
from .utils import parse_uuid


def _expert_dto(s) -> ExpertStatsDTO:
    return ExpertStatsDTO(expert_id=str(s.expert_id), total_requests=s.total_requests or 0,
                          completed_requests=s.completed_requests or 0, avg_rating=s.avg_rating or 0.0)


class AnalyticsService:
    STATS_TTL = 60

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None, cache: Optional[Cache] = None):
        self._session_factory = session_factory or get_session_factory()
        self._cache = cache or get_cache()

    def invalidate_cache(self) -> None:
        self._cache.invalidate_prefix("stats:")

    @staticmethod
    def _check_limit(limit: Optional[int]) -> None:
        if limit is not None and limit < 1:
            raise InvalidValueError("limit должен быть больше 0")

    def get_expert_stats(self, expert_id: str) -> ExpertStatsDTO:
        eid = parse_uuid(expert_id)
        with self._session_factory() as session:
            s = StatsRepository(session).get_expert_stats(eid)
            if s is None:
                raise NotFoundError(f"Статистика эксперта {expert_id} не найдена")
            return _expert_dto(s)

    def top_experts(self, sort_by: str = "completed_requests", descending: bool = True,
                    limit: Optional[int] = 5) -> list[ExpertStatsDTO]:
        if sort_by not in EXPERT_SORT:
            raise InvalidValueError(f"Сортировка по полю {sort_by} не поддерживается")
        self._check_limit(limit)

        def load():
            with self._session_factory() as session:
                return [dataclasses.asdict(_expert_dto(s))
                        for s in StatsRepository(session).list_expert_stats(sort_by, descending, limit)]

        rows = self._cache.get_or_load(f"stats:top:{sort_by}:{descending}:{limit}", self.STATS_TTL, load)
        return [ExpertStatsDTO(**r) for r in rows]

    def list_disease_stats(self, period: str, descending: bool = True, limit: Optional[int] = None) -> list[DiseaseStatsDTO]:
        self._check_limit(limit)

        def load():
            with self._session_factory() as session:
                return [dataclasses.asdict(DiseaseStatsDTO(disease_id=str(s.disease_id), count=s.count or 0,
                                                           period=s.period))
                        for s in StatsRepository(session).list_disease_stats(period, descending, limit)]

        rows = self._cache.get_or_load(f"stats:disease:{period}:{descending}:{limit}", self.STATS_TTL, load)
        return [DiseaseStatsDTO(**r) for r in rows]

    def event_counters(self, period: Optional[str] = None) -> list[EventCounterDTO]:
        with self._session_factory() as session:
            return [EventCounterDTO(event_type=c.event_type, period=c.period, count=c.count or 0, amount=c.amount or 0.0)
                    for c in StatsRepository(session).list_counters(period)]

    def platform_summary(self) -> PlatformSummaryDTO:
        def load():
            with self._session_factory() as session:
                stats = StatsRepository(session).list_expert_stats()
                total = sum(s.total_requests or 0 for s in stats)
                done = sum(s.completed_requests or 0 for s in stats)
                weight = sum(s.completed_requests or 0 for s in stats)
                rating = sum((s.avg_rating or 0) * (s.completed_requests or 0) for s in stats) / weight if weight else 0.0
                return dataclasses.asdict(PlatformSummaryDTO(
                    experts=len(stats), total_requests=total, completed_requests=done,
                    completion_rate=round(done * 100 / total, 1) if total else 0.0, avg_rating=round(rating, 2)))

        return PlatformSummaryDTO(**self._cache.get_or_load("stats:platform", self.STATS_TTL, load))
