import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import Diagnosis, ExpertResponse


class ResponseRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_by_request(self, request_id: uuid.UUID) -> list[ExpertResponse]:
        stmt = (select(ExpertResponse)
                .where(ExpertResponse.request_id == request_id)
                .order_by(ExpertResponse.created_at))
        return list(self.session.scalars(stmt).all())

    def list_by_expert(self, expert_id: uuid.UUID) -> list[ExpertResponse]:
        stmt = (select(ExpertResponse)
                .where(ExpertResponse.expert_id == expert_id)
                .order_by(ExpertResponse.created_at))
        return list(self.session.scalars(stmt).all())


class DiagnosisRepository:
    def __init__(self, session: Session):
        self.session = session

    def _base_query(self):
        return select(Diagnosis).options(selectinload(Diagnosis.checklist))

    def get_by_id(self, diagnosis_id: uuid.UUID) -> Optional[Diagnosis]:
        stmt = self._base_query().where(Diagnosis.id == diagnosis_id)
        return self.session.scalars(stmt).first()

    def get_by_request(self, request_id: uuid.UUID) -> Optional[Diagnosis]:
        stmt = self._base_query().where(Diagnosis.request_id == request_id)
        return self.session.scalars(stmt).first()
