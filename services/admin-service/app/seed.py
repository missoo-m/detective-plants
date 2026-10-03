
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session_factory
from .models import ExpertApplication

import uuid


def sid(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"plant-detective/{name}")


def seed(session_factory: Optional[Callable[[], Session]] = None) -> bool:
    factory = session_factory or get_session_factory()
    with factory() as session:
        if session.scalars(select(ExpertApplication)).first():
            return False
        session.add_all([
            ExpertApplication(id=sid("app-1"), user_id=sid("user-4"), documents_url="https://minio/docs/user-4.pdf",
                              status="PENDING", submitted_at=datetime(2026, 1, 18, 10, 0)),
            ExpertApplication(id=sid("app-2"), user_id=sid("user-2"), documents_url="https://minio/docs/user-2.pdf",
                              status="APPROVED", submitted_at=datetime(2026, 1, 3, 9, 0),
                              verified_at=datetime(2026, 1, 5, 12, 0)),
        ])
        session.commit()
        return True
