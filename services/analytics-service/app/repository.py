import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DiseaseStats, EventCounter, ExpertStats

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

    def bump_expert(self, expert_id: uuid.UUID, total: int = 0, completed: int = 0) -> None:
        stats = self.get_expert_stats(expert_id)
        if stats is None:
            stats = ExpertStats(expert_id=expert_id, total_requests=0, completed_requests=0, avg_rating=0)
            self.session.add(stats)
        stats.total_requests = (stats.total_requests or 0) + total
        stats.completed_requests = (stats.completed_requests or 0) + completed

    def bump_disease(self, disease_id: uuid.UUID, period: str) -> None:
        row = self.session.scalars(select(DiseaseStats).where(DiseaseStats.disease_id == disease_id,
                                                              DiseaseStats.period == period)).first()
        if row is None:
            row = DiseaseStats(disease_id=disease_id, period=period, count=0)
            self.session.add(row)
        row.count = (row.count or 0) + 1

    def bump_counter(self, event_type: str, period: str, amount: float = 0.0) -> None:
        row = self.session.scalars(select(EventCounter).where(EventCounter.event_type == event_type,
                                                              EventCounter.period == period)).first()
        if row is None:
            row = EventCounter(event_type=event_type, period=period, count=0, amount=0.0)
            self.session.add(row)
        row.count = (row.count or 0) + 1
        row.amount = (row.amount or 0.0) + amount

    def list_counters(self, period: Optional[str] = None) -> list[EventCounter]:
        stmt = select(EventCounter).order_by(EventCounter.period, EventCounter.event_type)
        if period:
            stmt = stmt.where(EventCounter.period == period)
        return list(self.session.scalars(stmt).all())
