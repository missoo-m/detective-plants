import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .models import Disease, Request

SORT_COLUMNS = {"created_at": Request.created_at, "status": Request.status}


class RequestRepository:
    def __init__(self, session: Session):
        self.session = session

    def _base_query(self):
        return select(Request).options(selectinload(Request.photos))

    def add(self, request: Request) -> None:
        self.session.add(request)

    def get_by_id(self, request_id: uuid.UUID) -> Optional[Request]:
        return self.session.scalars(self._base_query().where(Request.id == request_id)).first()

    def list_requests(self, client_id: Optional[uuid.UUID] = None, expert_id: Optional[uuid.UUID] = None,
                      statuses: Optional[list] = None, search: Optional[str] = None,
                      created_from: Optional[datetime] = None, created_to: Optional[datetime] = None,
                      has_expert: Optional[bool] = None, sort_by: str = "created_at",
                      descending: bool = False, limit: Optional[int] = None, offset: int = 0) -> list[Request]:
        stmt = self._base_query()
        if client_id:
            stmt = stmt.where(Request.client_id == client_id)
        if expert_id:
            stmt = stmt.where(Request.expert_id == expert_id)
        if statuses:
            stmt = stmt.where(Request.status.in_(statuses))
        if search:
            stmt = stmt.where(Request.symptoms.ilike(f"%{search}%"))
        if created_from:
            stmt = stmt.where(Request.created_at >= created_from)
        if created_to:
            stmt = stmt.where(Request.created_at <= created_to)
        if has_expert is True:
            stmt = stmt.where(Request.expert_id.is_not(None))
        elif has_expert is False:
            stmt = stmt.where(Request.expert_id.is_(None))
        column = SORT_COLUMNS[sort_by]
        stmt = stmt.order_by(column.desc() if descending else column.asc(), Request.id)
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).all())

    def count_by_status(self, client_id: Optional[uuid.UUID] = None,
                        expert_id: Optional[uuid.UUID] = None) -> dict:
        stmt = select(Request.status, func.count(Request.id)).group_by(Request.status)
        if client_id:
            stmt = stmt.where(Request.client_id == client_id)
        if expert_id:
            stmt = stmt.where(Request.expert_id == expert_id)
        return {status: count for status, count in self.session.execute(stmt).all()}


class DiseaseRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, disease_id: uuid.UUID) -> Optional[Disease]:
        return self.session.get(Disease, disease_id)

    def list_all(self) -> list[Disease]:
        return list(self.session.scalars(select(Disease).order_by(Disease.name)).all())
