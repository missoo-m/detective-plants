from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session_factory
from .models import RecoveryTracker, TreatmentHistory

import uuid


def sid(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"plant-detective/{name}")


def seed(session_factory: Optional[Callable[[], Session]] = None) -> bool:
    factory = session_factory or get_session_factory()
    with factory() as session:
        if session.scalars(select(RecoveryTracker)).first():
            return False
        tracker = RecoveryTracker(
            id=sid("track-1"), request_id=sid("req-2"), client_id=sid("user-1"), expert_id=sid("user-2"),
            start_date=datetime(2026, 1, 16, 12, 0), end_date=datetime(2026, 1, 30, 12, 0),
            status="ACTIVE", current_stage="START")
        tracker.history = [
            TreatmentHistory(id=sid("h-1"), record_type="TREATMENT_UPDATE", date=datetime(2026, 1, 17, 10, 0),
                             change_description="Начало лечения", author_id=sid("user-2")),
            TreatmentHistory(id=sid("h-2"), record_type="PHOTO", date=datetime(2026, 1, 18, 9, 0),
                             photo_url="https://minio/track-1/photo1.jpg", author_id=sid("user-1")),
        ]
        session.add(tracker)
        session.commit()
        return True
