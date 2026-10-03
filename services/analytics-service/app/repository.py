import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DiseaseStats, ExpertStats


class StatsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_expert_stats(self, expert_id: uuid.UUID) -> Optional[ExpertStats]:
        return self.session.scalars(select(ExpertStats).where(ExpertStats.expert_id == expert_id)).first()

    def list_disease_stats(self, period: str) -> list[DiseaseStats]:
        stmt = select(DiseaseStats).where(DiseaseStats.period == period).order_by(DiseaseStats.count.desc())
        return list(self.session.scalars(stmt).all())
