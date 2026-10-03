import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Field, NdviMeasurement, SatelliteAlert


class FieldRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, field_id: uuid.UUID) -> Optional[Field]:
        return self.session.get(Field, field_id)

    def list_fields(self, owner_id: uuid.UUID) -> list[Field]:
        stmt = select(Field).where(Field.owner_id == owner_id).order_by(Field.created_at)
        return list(self.session.scalars(stmt).all())

    def list_measurements(self, field_id: uuid.UUID) -> list[NdviMeasurement]:
        stmt = (select(NdviMeasurement).where(NdviMeasurement.field_id == field_id)
                .order_by(NdviMeasurement.measured_at))
        return list(self.session.scalars(stmt).all())

    def list_alerts(self, field_id: Optional[uuid.UUID] = None) -> list[SatelliteAlert]:
        stmt = select(SatelliteAlert)
        if field_id:
            stmt = stmt.where(SatelliteAlert.field_id == field_id)
        return list(self.session.scalars(stmt.order_by(SatelliteAlert.created_at)).all())
