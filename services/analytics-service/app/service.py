from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .errors import NotFoundError
from .repository import StatsRepository
from .schemas import DiseaseStatsDTO, ExpertStatsDTO
from .utils import parse_uuid


class AnalyticsService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    def get_expert_stats(self, expert_id: str) -> ExpertStatsDTO:
        eid = parse_uuid(expert_id)
        with self._session_factory() as session:
            s = StatsRepository(session).get_expert_stats(eid)
            if s is None:
                raise NotFoundError(f"Статистика эксперта {expert_id} не найдена")
            return ExpertStatsDTO(expert_id=str(s.expert_id), total_requests=s.total_requests or 0,
                                  completed_requests=s.completed_requests or 0, avg_rating=s.avg_rating or 0.0)

    def list_disease_stats(self, period: str) -> list[DiseaseStatsDTO]:
        with self._session_factory() as session:
            return [DiseaseStatsDTO(disease_id=str(s.disease_id), count=s.count or 0, period=s.period)
                    for s in StatsRepository(session).list_disease_stats(period)]
