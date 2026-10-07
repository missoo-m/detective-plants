import copy
import json
from typing import Optional

from ..errors import BusinessRuleError, NotFoundError, ValidationError
from .base import SatelliteClientBase
from .common import new_id, now_iso

MAX_FIELDS_PER_OWNER = 10
ALERT_TYPES = {"NDVI_DROP", "WEATHER", "DISEASE_RISK"}
_GEOMETRY = '{"type": "Polygon", "coordinates": [[[27.55, 53.90], [27.56, 53.90], [27.56, 53.91], [27.55, 53.91], [27.55, 53.90]]]}'

MOCK_FIELDS = {
    "fld-1": {"id": "fld-1", "owner_id": "user-1", "name": "Теплица №1", "geometry": _GEOMETRY,
              "created_at": "2026-01-10T12:00:00Z"},
    "fld-2": {"id": "fld-2", "owner_id": "user-1", "name": "Огород у дома", "geometry": _GEOMETRY,
              "created_at": "2026-01-11T09:00:00Z"},
}

MOCK_MEASUREMENTS = [
    {"id": "ndvi-1", "field_id": "fld-1", "ndvi_value": 0.62, "measured_at": "2026-01-10T10:00:00Z"},
    {"id": "ndvi-2", "field_id": "fld-1", "ndvi_value": 0.55, "measured_at": "2026-01-17T10:00:00Z"},
    {"id": "ndvi-3", "field_id": "fld-2", "ndvi_value": 0.71, "measured_at": "2026-01-12T10:00:00Z"},
]

MOCK_ALERTS = [
    {"id": "alert-1", "field_id": "fld-1", "type": "NDVI_DROP", "message": "Снижение NDVI на 11% за неделю",
     "created_at": "2026-01-17T12:00:00Z"},
]


def validate_polygon(geometry: str) -> None:
    try:
        data = json.loads(geometry)
    except (TypeError, ValueError):
        raise ValidationError("Границы поля должны быть корректным GeoJSON")
    if not isinstance(data, dict) or data.get("type") != "Polygon":
        raise ValidationError("Поддерживается только геометрия типа Polygon")
    try:
        points = [(float(lon), float(lat)) for lon, lat in data["coordinates"][0]]
    except (KeyError, IndexError, TypeError, ValueError):
        raise ValidationError("Некорректный формат координат полигона")
    if len(points) < 4 or points[0] != points[-1]:
        raise ValidationError("Кольцо полигона должно быть замкнуто и содержать не менее 4 точек")
    if any(not -180 <= lon <= 180 or not -90 <= lat <= 90 for lon, lat in points):
        raise ValidationError("Координаты выходят за допустимые пределы")


class MockSatelliteClient(SatelliteClientBase):
    #Mock Satellite Service

    def __init__(self):
        self.fields = copy.deepcopy(MOCK_FIELDS)
        self.measurements = copy.deepcopy(MOCK_MEASUREMENTS)
        self.alerts = copy.deepcopy(MOCK_ALERTS)

    def list_fields(self, owner_id: str) -> list[dict]:
        return sorted((f for f in self.fields.values() if f["owner_id"] == owner_id), key=lambda f: f["created_at"])

    def get_field(self, field_id: str) -> dict:
        field = self.fields.get(field_id)
        if not field:
            raise NotFoundError(f"Поле {field_id} не найдено")
        return field

    def list_measurements(self, field_id: str, descending=False, limit=None) -> list[dict]:
        if limit is not None and limit < 1:
            raise ValidationError("limit должен быть больше 0")
        items = sorted((m for m in self.measurements if m["field_id"] == field_id),
                       key=lambda m: m["measured_at"], reverse=descending)
        return items[:limit] if limit else items

    def list_alerts(self, field_id=None, owner_id=None, alert_type=None, descending=True) -> list[dict]:
        if alert_type is not None and alert_type not in ALERT_TYPES:
            raise ValidationError(f"Неизвестный тип предупреждения: {alert_type}")
        items = list(self.alerts)
        if field_id:
            items = [a for a in items if a["field_id"] == field_id]
        if owner_id:
            items = [a for a in items if self.fields[a["field_id"]]["owner_id"] == owner_id]
        if alert_type:
            items = [a for a in items if a["type"] == alert_type]
        return sorted(items, key=lambda a: a["created_at"], reverse=descending)

    def ndvi_summary(self, field_id: str) -> dict:
        self.get_field(field_id)
        items = self.list_measurements(field_id)
        if not items:
            raise NotFoundError(f"Для поля {field_id} нет измерений NDVI")
        values = [m["ndvi_value"] for m in items]
        trend = values[-1] - values[-2] if len(values) > 1 else 0.0
        return {"field_id": field_id, "count": len(values), "min_value": min(values), "max_value": max(values),
                "avg_value": round(sum(values) / len(values), 3), "last_value": values[-1], "trend": round(trend, 3)}

    def create_field(self, owner_id: str, name: str, geometry: str) -> dict:
        name = (name or "").strip()
        if not 1 <= len(name) <= 100:
            raise ValidationError("Название поля должно содержать от 1 до 100 символов")
        validate_polygon(geometry)
        own = self.list_fields(owner_id)
        if len(own) >= MAX_FIELDS_PER_OWNER:
            raise BusinessRuleError(f"Нельзя добавить более {MAX_FIELDS_PER_OWNER} полей")
        if any(f["name"].lower() == name.lower() for f in own):
            raise BusinessRuleError("Поле с таким названием уже существует")
        field = {"id": new_id("fld"), "owner_id": owner_id, "name": name, "geometry": geometry, "created_at": now_iso()}
        self.fields[field["id"]] = field
        return field
