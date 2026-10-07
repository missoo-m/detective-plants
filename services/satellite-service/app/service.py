import json
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .errors import BusinessRuleError, InvalidValueError, NotFoundError
from .models import Field, NdviMeasurement, SatelliteAlert, utcnow
from .repository import FieldRepository
from .schemas import AlertDTO, FieldDTO, MeasurementDTO, NdviSummaryDTO
from .utils import fmt_dt, parse_uuid

MAX_FIELDS_PER_OWNER = 10
NDVI_DROP_THRESHOLD = 0.10          
ALERT_TYPES = {"NDVI_DROP", "WEATHER", "DISEASE_RISK"}


def _field(f: Field) -> FieldDTO:
    return FieldDTO(id=str(f.id), owner_id=str(f.owner_id), name=f.name, geometry=f.geometry,
                    created_at=fmt_dt(f.created_at))


def _measurement(m: NdviMeasurement) -> MeasurementDTO:
    return MeasurementDTO(id=str(m.id), field_id=str(m.field_id), ndvi_value=m.ndvi_value,
                          measured_at=fmt_dt(m.measured_at))


def _alert(a: SatelliteAlert) -> AlertDTO:
    return AlertDTO(id=str(a.id), field_id=str(a.field_id), type=a.type, message=a.message,
                    created_at=fmt_dt(a.created_at))


def validate_polygon(geometry: str) -> None:
    try:
        data = json.loads(geometry)
    except (TypeError, ValueError):
        raise InvalidValueError("Границы поля должны быть корректным GeoJSON")
    if not isinstance(data, dict) or data.get("type") != "Polygon":
        raise InvalidValueError("Поддерживается только геометрия типа Polygon")
    try:
        ring = data["coordinates"][0]
        points = [(float(lon), float(lat)) for lon, lat in ring]
    except (KeyError, IndexError, TypeError, ValueError):
        raise InvalidValueError("Некорректный формат координат полигона")
    if len(points) < 4 or points[0] != points[-1]:
        raise InvalidValueError("Кольцо полигона должно быть замкнуто и содержать не менее 4 точек")
    if any(not -180 <= lon <= 180 or not -90 <= lat <= 90 for lon, lat in points):
        raise InvalidValueError("Координаты выходят за допустимые пределы")


class SatelliteService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    def get_field(self, field_id: str) -> FieldDTO:
        with self._session_factory() as session:
            field = FieldRepository(session).get_by_id(parse_uuid(field_id))
            if field is None:
                raise NotFoundError(f"Поле {field_id} не найдено")
            return _field(field)

    def list_fields(self, owner_id: str) -> list[FieldDTO]:
        oid = parse_uuid(owner_id)
        with self._session_factory() as session:
            return [_field(f) for f in FieldRepository(session).list_fields(oid)]

    def list_measurements(self, field_id: str, descending: bool = False, limit: Optional[int] = None) -> list[MeasurementDTO]:
        if limit is not None and limit < 1:
            raise InvalidValueError("limit должен быть больше 0")
        fid = parse_uuid(field_id)
        with self._session_factory() as session:
            return [_measurement(m) for m in FieldRepository(session).list_measurements(fid, descending, limit)]

    def list_alerts(self, field_id: Optional[str] = None, owner_id: Optional[str] = None,
                    alert_type: Optional[str] = None, descending: bool = True) -> list[AlertDTO]:
        if alert_type is not None and alert_type not in ALERT_TYPES:
            raise InvalidValueError(f"Неизвестный тип предупреждения: {alert_type}")
        fid = parse_uuid(field_id) if field_id else None
        oid = parse_uuid(owner_id) if owner_id else None
        with self._session_factory() as session:
            return [_alert(a) for a in FieldRepository(session).list_alerts(fid, oid, alert_type, descending)]

    def ndvi_summary(self, field_id: str) -> NdviSummaryDTO:
        fid = parse_uuid(field_id)
        with self._session_factory() as session:
            repo = FieldRepository(session)
            if repo.get_by_id(fid) is None:
                raise NotFoundError(f"Поле {field_id} не найдено")
            count, low, high, avg = repo.ndvi_stats(fid)
            if not count:
                raise NotFoundError(f"Для поля {field_id} нет измерений NDVI")
            last = repo.list_measurements(fid, descending=True, limit=2)
            trend = last[0].ndvi_value - last[1].ndvi_value if len(last) > 1 else 0.0
            return NdviSummaryDTO(field_id=field_id, count=count, min_value=low, max_value=high,
                                  avg_value=round(avg, 3), last_value=last[0].ndvi_value, trend=round(trend, 3))

    def create_field(self, owner_id: str, name: str, geometry: str) -> FieldDTO:
        oid = parse_uuid(owner_id)
        name = (name or "").strip()
        if not 1 <= len(name) <= 100:
            raise InvalidValueError("Название поля должно содержать от 1 до 100 символов")
        validate_polygon(geometry)
        with self._session_factory() as session:
            repo = FieldRepository(session)
            if repo.count_fields(oid) >= MAX_FIELDS_PER_OWNER:
                raise BusinessRuleError(f"Нельзя добавить более {MAX_FIELDS_PER_OWNER} полей")
            if repo.name_exists(oid, name):
                raise BusinessRuleError("Поле с таким названием уже существует")
            field = Field(owner_id=oid, name=name, geometry=geometry)
            repo.add(field)
            session.commit()
            return _field(field)

    def record_measurement(self, field_id: str, ndvi_value: float, measured_at: Optional[datetime] = None) -> MeasurementDTO:
        if not -1.0 <= ndvi_value <= 1.0:
            raise InvalidValueError("NDVI должен находиться в диапазоне от -1 до 1")
        fid = parse_uuid(field_id)
        when = measured_at or utcnow()
        with self._session_factory() as session:
            repo = FieldRepository(session)
            if repo.get_by_id(fid) is None:
                raise NotFoundError(f"Поле {field_id} не найдено")
            previous = repo.list_measurements(fid, descending=True, limit=1)
            if previous and when <= previous[0].measured_at:
                raise BusinessRuleError("Измерение должно быть новее последнего сохранённого")
            measurement = NdviMeasurement(field_id=fid, ndvi_value=ndvi_value, measured_at=when)
            repo.add(measurement)
            if previous and previous[0].ndvi_value > 0:
                drop = (previous[0].ndvi_value - ndvi_value) / previous[0].ndvi_value
                if drop >= NDVI_DROP_THRESHOLD:
                    repo.add(SatelliteAlert(field_id=fid, type="NDVI_DROP", created_at=when,
                                            message=f"Снижение NDVI на {round(drop * 100)}% с прошлого измерения"))
            session.commit()
            return _measurement(measurement)
