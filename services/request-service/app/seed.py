
import uuid
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session_factory
from .models import Disease, Request, RequestPhoto


def sid(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"plant-detective/{name}")


DISEASES = [
    ("dis-1", "Мучнистая роса", "Грибковое заболевание", "Белый налёт на листьях", "Обработка фунгицидами"),
    ("dis-2", "Корневая гниль", "Загнивание корней", "Пожелтение, увядание", "Пересадка, дренаж"),
]


def seed(session_factory: Optional[Callable[[], Session]] = None) -> bool:
    factory = session_factory or get_session_factory()
    with factory() as session:
        if session.scalars(select(Disease)).first():
            return False

        for key, name, desc, symptoms, treatment in DISEASES:
            session.add(Disease(id=sid(key), name=name, description=desc,
                                symptoms=symptoms, treatment=treatment))

        req1 = Request(id=sid("req-1"), client_id=sid("user-1"), expert_id=None,
                       symptoms="Пожелтение листьев, пятна", ai_prediagnosis="Возможно мучнистая роса",
                       status="CREATED", created_at=datetime(2026, 1, 15, 10, 30))
        req1.photos = [
            RequestPhoto(id=sid("p-1"), url="https://minio/req-1/photo1.jpg", uploaded_at=datetime(2026, 1, 15, 10, 30)),
            RequestPhoto(id=sid("p-2"), url="https://minio/req-1/photo2.jpg", uploaded_at=datetime(2026, 1, 15, 10, 31)),
        ]
        req2 = Request(id=sid("req-2"), client_id=sid("user-1"), expert_id=sid("user-2"),
                       symptoms="Белый налёт на листьях", ai_prediagnosis="Мучнистая роса",
                       status="IN_PROGRESS", created_at=datetime(2026, 1, 16, 11, 0))
        req3 = Request(id=sid("req-3"), client_id=sid("user-4"), expert_id=None,
                       symptoms="Сохнут кончики листьев", ai_prediagnosis=None,
                       status="CREATED", created_at=datetime(2026, 1, 17, 9, 0))
        req4 = Request(id=sid("req-4"), client_id=sid("user-4"), expert_id=sid("user-2"),
                       symptoms="Скручивание молодых листьев", ai_prediagnosis=None,
                       status="DONE", created_at=datetime(2026, 1, 5, 9, 0), completed_at=datetime(2026, 1, 12, 18, 0))
        req5 = Request(id=sid("req-5"), client_id=sid("user-1"), expert_id=None,
                       symptoms="Вялость растения после пересадки", ai_prediagnosis=None,
                       status="CANCELLED", created_at=datetime(2026, 1, 3, 14, 0), completed_at=datetime(2026, 1, 3, 15, 0))
        session.add_all([req1, req2, req3, req4, req5])
        session.commit()
        return True
