from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session_factory
from .models import DiseaseStats, ExpertStats

import uuid


def sid(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"plant-detective/{name}")


def seed(session_factory: Optional[Callable[[], Session]] = None) -> bool:
    factory = session_factory or get_session_factory()
    with factory() as session:
        if session.scalars(select(ExpertStats)).first():
            return False
        session.add(ExpertStats(id=sid("estats-1"), expert_id=sid("user-2"), total_requests=2,
                                completed_requests=1, avg_rating=4.8, updated_at=datetime(2026, 1, 20, 0, 0)))
        session.add_all([
            DiseaseStats(id=sid("dstats-1"), disease_id=sid("dis-1"), count=3, period="2026-01"),
            DiseaseStats(id=sid("dstats-2"), disease_id=sid("dis-2"), count=1, period="2026-01"),
            DiseaseStats(id=sid("dstats-3"), disease_id=sid("dis-1"), count=1, period="2025-12"),
        ])
        session.commit()
        return True
