from typing import Optional
from .base import NotFoundError, SatelliteClientBase

_GEOMETRY = '{"type": "Polygon", "coordinates": [[[27.55, 53.90], [27.56, 53.90], [27.56, 53.91], [27.55, 53.91], [27.55, 53.90]]]}'

MOCK_FIELDS = {
    "fld-1": {"id": "fld-1", "owner_id": "user-1", "name": "Теплица №1",
              "geometry": _GEOMETRY, "created_at": "2026-01-10T12:00:00Z"},
    "fld-2": {"id": "fld-2", "owner_id": "user-1", "name": "Огород у дома",
              "geometry": _GEOMETRY, "created_at": "2026-01-11T09:00:00Z"},
}

MOCK_MEASUREMENTS = [
    {"id": "ndvi-1", "field_id": "fld-1", "ndvi_value": 0.62, "measured_at": "2026-01-10T10:00:00Z"},
    {"id": "ndvi-2", "field_id": "fld-1", "ndvi_value": 0.55, "measured_at": "2026-01-17T10:00:00Z"},
    {"id": "ndvi-3", "field_id": "fld-2", "ndvi_value": 0.71, "measured_at": "2026-01-12T10:00:00Z"},
]

MOCK_ALERTS = [
    {"id": "alert-1", "field_id": "fld-1", "type": "NDVI_DROP",
     "message": "Снижение NDVI на 11% за неделю", "created_at": "2026-01-17T12:00:00Z"},
]


class MockSatelliteClient(SatelliteClientBase):
    #Mock-клиент Satellite Service

    def list_fields(self, owner_id: str) -> list[dict]:
        return [f for f in MOCK_FIELDS.values() if f["owner_id"] == owner_id]

    def get_field(self, field_id: str) -> dict:
        field = MOCK_FIELDS.get(field_id)
        if not field:
            raise NotFoundError(f"Поле {field_id} не найдено")
        return field

    def list_measurements(self, field_id: str) -> list[dict]:
        return [m for m in MOCK_MEASUREMENTS if m["field_id"] == field_id]

    def list_alerts(self, field_id: Optional[str] = None) -> list[dict]:
        return [a for a in MOCK_ALERTS if not field_id or a["field_id"] == field_id]
