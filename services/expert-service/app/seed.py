import uuid
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session_factory
from .models import Diagnosis, ExpertResponse, MLTrainingExample, TreatmentChecklist


def sid(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"plant-detective/{name}")


def seed(session_factory: Optional[Callable[[], Session]] = None) -> bool:
    factory = session_factory or get_session_factory()
    with factory() as session:
        if session.scalars(select(ExpertResponse)).first():
            return False

        session.add_all([
            ExpertResponse(id=sid("resp-1"), request_id=sid("req-1"), expert_id=sid("user-2"),
                           comment="Готов взять заявку, похоже на мучнистую росу",
                           status="PENDING", created_at=datetime(2026, 1, 15, 11, 0)),
            ExpertResponse(id=sid("resp-2"), request_id=sid("req-2"), expert_id=sid("user-2"),
                           comment="Беру в работу", status="ACCEPTED",
                           created_at=datetime(2026, 1, 16, 11, 30)),
        ])

        diagnosis = Diagnosis(
            id=sid("diag-1"), request_id=sid("req-2"), expert_id=sid("user-2"),
            disease_id=sid("dis-1"), description="Мучнистая роса на листьях томата",
            ai_prediagnosis="Мучнистая роса", duration_days=14,
            created_at=datetime(2026, 1, 16, 12, 0),
        )
        diagnosis.checklist = [
            TreatmentChecklist(id=sid("step-1"), position=1, step="Удалить поражённые листья",
                               frequency="однократно", duration_days=1),
            TreatmentChecklist(id=sid("step-2"), position=2, step="Обработать фунгицидом",
                               frequency="раз в 5 дней", duration_days=14),
        ]
        session.add(diagnosis)

        session.add(MLTrainingExample(id=sid("ml-1"), request_id=sid("req-2"),
                                      ai_prediagnosis="Мучнистая роса",
                                      expert_correction="Подтверждено: мучнистая роса",
                                      created_at=datetime(2026, 1, 16, 12, 0)))
        session.commit()
        return True
