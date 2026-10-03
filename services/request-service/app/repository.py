import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import Disease, Request


class RequestRepository:
    def __init__(self, session: Session):
        self.session = session

    def _base_query(self):
        return select(Request).options(selectinload(Request.photos))

    def get_by_id(self, request_id: uuid.UUID) -> Optional[Request]:
        stmt = self._base_query().where(Request.id == request_id)
        return self.session.scalars(stmt).first()

    def list_requests(self, client_id: Optional[uuid.UUID] = None,
                      expert_id: Optional[uuid.UUID] = None,
                      status: Optional[str] = None) -> list[Request]:
        stmt = self._base_query()
        if client_id:
            stmt = stmt.where(Request.client_id == client_id)
        if expert_id:
            stmt = stmt.where(Request.expert_id == expert_id)
        if status:
            stmt = stmt.where(Request.status == status)
        stmt = stmt.order_by(Request.created_at)
        return list(self.session.scalars(stmt).all())


class DiseaseRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, disease_id: uuid.UUID) -> Optional[Disease]:
        return self.session.get(Disease, disease_id)

    def list_all(self) -> list[Disease]:
        return list(self.session.scalars(select(Disease).order_by(Disease.name)).all())
