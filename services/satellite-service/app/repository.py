import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Field, NdviMeasurement, SatelliteAlert


class FieldRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, obj) -> None:
        self.session.add(obj)

    def get_by_id(self, field_id: uuid.UUID) -> Optional[Field]:
        return self.session.get(Field, field_id)

    def list_fields(self, owner_id: uuid.UUID) -> list[Field]:
        return list(self.session.scalars(select(Field).where(Field.owner_id == owner_id).order_by(Field.created_at)).all())

    def count_fields(self, owner_id: uuid.UUID) -> int:
        return self.session.scalar(select(func.count(Field.id)).where(Field.owner_id == owner_id)) or 0

    def name_exists(self, owner_id: uuid.UUID, name: str) -> bool:
        names = self.session.scalars(select(Field.name).where(Field.owner_id == owner_id)).all()
        return any(n.lower() == name.lower() for n in names)     

    def list_measurements(self, field_id: uuid.UUID, descending: bool = False,
                          limit: Optional[int] = None) -> list[NdviMeasurement]:
        column = NdviMeasurement.measured_at
        stmt = select(NdviMeasurement).where(NdviMeasurement.field_id == field_id)
        stmt = stmt.order_by(column.desc() if descending else column.asc())
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).all())

    def ndvi_stats(self, field_id: uuid.UUID):
        stmt = select(func.count(NdviMeasurement.id), func.min(NdviMeasurement.ndvi_value),
                      func.max(NdviMeasurement.ndvi_value), func.avg(NdviMeasurement.ndvi_value)
                      ).where(NdviMeasurement.field_id == field_id)
        return self.session.execute(stmt).one()

    def list_alerts(self, field_id: Optional[uuid.UUID] = None, owner_id: Optional[uuid.UUID] = None,
                    alert_type: Optional[str] = None, descending: bool = True) -> list[SatelliteAlert]:
        stmt = select(SatelliteAlert)
        if field_id:
            stmt = stmt.where(SatelliteAlert.field_id == field_id)
        if owner_id:
            stmt = stmt.join(Field, Field.id == SatelliteAlert.field_id).where(Field.owner_id == owner_id)
        if alert_type:
            stmt = stmt.where(SatelliteAlert.type == alert_type)
        column = SatelliteAlert.created_at
        return list(self.session.scalars(stmt.order_by(column.desc() if descending else column.asc())).all())
