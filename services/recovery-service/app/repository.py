import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import RecoveryTracker

SORT_COLUMNS = {"start_date": RecoveryTracker.start_date, "end_date": RecoveryTracker.end_date,
                "status": RecoveryTracker.status}


class TrackerRepository:
    def __init__(self, session: Session):
        self.session = session

    def _base_query(self):
        return select(RecoveryTracker).options(selectinload(RecoveryTracker.history))

    def add(self, obj) -> None:
        self.session.add(obj)

    def get_by_id(self, tracker_id: uuid.UUID) -> Optional[RecoveryTracker]:
        return self.session.scalars(self._base_query().where(RecoveryTracker.id == tracker_id)).first()

    def get_by_request(self, request_id: uuid.UUID) -> Optional[RecoveryTracker]:
        return self.session.scalars(self._base_query().where(RecoveryTracker.request_id == request_id)).first()

    def list_trackers(self, client_id: Optional[uuid.UUID] = None, expert_id: Optional[uuid.UUID] = None,
                      status: Optional[str] = None, sort_by: str = "start_date",
                      descending: bool = False) -> list[RecoveryTracker]:
        stmt = self._base_query()
        if client_id:
            stmt = stmt.where(RecoveryTracker.client_id == client_id)
        if expert_id:
            stmt = stmt.where(RecoveryTracker.expert_id == expert_id)
        if status:
            stmt = stmt.where(RecoveryTracker.status == status)
        column = SORT_COLUMNS[sort_by]
        return list(self.session.scalars(stmt.order_by(column.desc() if descending else column.asc())).all())
