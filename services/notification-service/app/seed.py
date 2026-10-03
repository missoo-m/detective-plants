from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session_factory
from .models import Notification

import uuid


def sid(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"plant-detective/{name}")


def seed(session_factory: Optional[Callable[[], Session]] = None) -> bool:
    factory = session_factory or get_session_factory()
    with factory() as session:
        if session.scalars(select(Notification)).first():
            return False
        session.add_all([
            Notification(id=sid("notif-1"), user_id=sid("user-1"), type="REQUEST_CREATED",
                         message="Ваша заявка создана", status="UNREAD", created_at=datetime(2026, 1, 15, 10, 30)),
            Notification(id=sid("notif-2"), user_id=sid("user-1"), type="DIAGNOSIS_READY",
                         message="Диагноз готов", status="READ", created_at=datetime(2026, 1, 16, 12, 10)),
            Notification(id=sid("notif-3"), user_id=sid("user-2"), type="PAYMENT_RECEIVED",
                         message="Оплата получена", status="UNREAD", created_at=datetime(2026, 1, 16, 12, 5)),
        ])
        session.commit()
        return True
