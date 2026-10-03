from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .errors import NotFoundError
from .models import Field, NdviMeasurement, SatelliteAlert
from .repository import FieldRepository
from .schemas import AlertDTO, FieldDTO, MeasurementDTO
from .utils import fmt_dt, parse_uuid


def _field(f: Field) -> FieldDTO:
    return FieldDTO(id=str(f.id), owner_id=str(f.owner_id), name=f.name, geometry=f.geometry,
                    created_at=fmt_dt(f.created_at))


def _measurement(m: NdviMeasurement) -> MeasurementDTO:
    return MeasurementDTO(id=str(m.id), field_id=str(m.field_id), ndvi_value=m.ndvi_value,
                          measured_at=fmt_dt(m.measured_at))


def _alert(a: SatelliteAlert) -> AlertDTO:
    return AlertDTO(id=str(a.id), field_id=str(a.field_id), type=a.type, message=a.message,
                    created_at=fmt_dt(a.created_at))


class SatelliteService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    def get_field(self, field_id: str) -> FieldDTO:
        fid = parse_uuid(field_id)
        with self._session_factory() as session:
            field = FieldRepository(session).get_by_id(fid)
            if field is None:
                raise NotFoundError(f"Поле {field_id} не найдено")
            return _field(field)

    def list_fields(self, owner_id: str) -> list[FieldDTO]:
        oid = parse_uuid(owner_id)
        with self._session_factory() as session:
            return [_field(f) for f in FieldRepository(session).list_fields(oid)]

    def list_measurements(self, field_id: str) -> list[MeasurementDTO]:
        fid = parse_uuid(field_id)
        with self._session_factory() as session:
            return [_measurement(m) for m in FieldRepository(session).list_measurements(fid)]

    def list_alerts(self, field_id: Optional[str] = None) -> list[AlertDTO]:
        fid = parse_uuid(field_id) if field_id else None
        with self._session_factory() as session:
            return [_alert(a) for a in FieldRepository(session).list_alerts(fid)]
