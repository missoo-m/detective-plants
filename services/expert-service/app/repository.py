import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .models import Diagnosis, ExpertResponse, MLTrainingExample


class ResponseRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, obj) -> None:
        self.session.add(obj)

    def get(self, request_id: uuid.UUID, expert_id: uuid.UUID) -> Optional[ExpertResponse]:
        stmt = select(ExpertResponse).where(ExpertResponse.request_id == request_id,
                                            ExpertResponse.expert_id == expert_id)
        return self.session.scalars(stmt).first()

    def list_by_request(self, request_id: uuid.UUID) -> list[ExpertResponse]:
        stmt = (select(ExpertResponse).where(ExpertResponse.request_id == request_id)
                .order_by(ExpertResponse.created_at))
        return list(self.session.scalars(stmt).all())

    def list_by_expert(self, expert_id: uuid.UUID, status: Optional[str] = None,
                       descending: bool = False) -> list[ExpertResponse]:
        stmt = select(ExpertResponse).where(ExpertResponse.expert_id == expert_id)
        if status:
            stmt = stmt.where(ExpertResponse.status == status)
        column = ExpertResponse.created_at
        return list(self.session.scalars(stmt.order_by(column.desc() if descending else column.asc())).all())

    def count_by_status(self, expert_id: uuid.UUID) -> dict:
        stmt = (select(ExpertResponse.status, func.count(ExpertResponse.id))
                .where(ExpertResponse.expert_id == expert_id).group_by(ExpertResponse.status))
        return {status: count for status, count in self.session.execute(stmt).all()}


class DiagnosisRepository:
    def __init__(self, session: Session):
        self.session = session

    def _base_query(self):
        return select(Diagnosis).options(selectinload(Diagnosis.checklist))

    def add(self, obj) -> None:
        self.session.add(obj)

    def get_by_id(self, diagnosis_id: uuid.UUID) -> Optional[Diagnosis]:
        return self.session.scalars(self._base_query().where(Diagnosis.id == diagnosis_id)).first()

    def get_by_request(self, request_id: uuid.UUID) -> Optional[Diagnosis]:
        return self.session.scalars(self._base_query().where(Diagnosis.request_id == request_id)).first()

    def add_ml_example(self, example: MLTrainingExample) -> None:
        self.session.add(example)
