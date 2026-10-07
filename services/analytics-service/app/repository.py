import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DiseaseStats, ExpertStats

EXPERT_SORT = {"total_requests": ExpertStats.total_requests, "completed_requests": ExpertStats.completed_requests,
               "avg_rating": ExpertStats.avg_rating}
DISEASE_SORT = {"count": DiseaseStats.count}


class StatsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_expert_stats(self, expert_id: uuid.UUID) -> Optional[ExpertStats]:
        return self.session.scalars(select(ExpertStats).where(ExpertStats.expert_id == expert_id)).first()

    def list_expert_stats(self, sort_by: str = "completed_requests", descending: bool = True,
                          limit: Optional[int] = None) -> list[ExpertStats]:
        column = EXPERT_SORT[sort_by]
        stmt = select(ExpertStats).order_by(column.desc() if descending else column.asc(), ExpertStats.expert_id)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).all())

    def list_disease_stats(self, period: str, descending: bool = True, limit: Optional[int] = None) -> list[DiseaseStats]:
        stmt = select(DiseaseStats).where(DiseaseStats.period == period)
        stmt = stmt.order_by(DiseaseStats.count.desc() if descending else DiseaseStats.count.asc(), DiseaseStats.id)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).all())
