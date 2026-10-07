import json
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.errors import BusinessRuleError, InvalidValueError, NotFoundError
from app.models import Base
from app.seed import seed, sid
from app.service import SatelliteService

U1, U4 = str(sid("user-1")), str(sid("user-4"))
F1, F2 = str(sid("fld-1")), str(sid("fld-2"))
SQUARE = json.dumps({"type": "Polygon", "coordinates": [[[27.5, 53.9], [27.6, 53.9], [27.6, 54.0], [27.5, 54.0], [27.5, 53.9]]]})


@pytest.fixture
def service():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    assert seed(factory) is True
    assert seed(factory) is False
    return SatelliteService(factory)


def test_reads_and_sort(service):
    assert [f.name for f in service.list_fields(U1)] == ["Теплица №1", "Огород у дома"]
    assert [m.ndvi_value for m in service.list_measurements(F1)] == [0.62, 0.55]
    assert [m.ndvi_value for m in service.list_measurements(F1, descending=True, limit=1)] == [0.55]
    assert service.list_alerts(owner_id=U1)[0].type == "NDVI_DROP" and service.list_alerts(F2) == []
    assert service.list_alerts(alert_type="WEATHER") == []
    with pytest.raises(InvalidValueError):
        service.list_alerts(alert_type="BAD")
    with pytest.raises(NotFoundError):
        service.get_field(str(sid("fld-999")))


def test_ndvi_summary(service):
    s = service.ndvi_summary(F1)
    assert (s.count, s.min_value, s.max_value, s.avg_value, s.last_value, s.trend) == (2, 0.55, 0.62, 0.585, 0.55, -0.07)
    assert service.ndvi_summary(F2).trend == 0.0
    with pytest.raises(NotFoundError):
        service.ndvi_summary(str(sid("fld-999")))


def test_create_field(service):
    f = service.create_field(U4, "  Моя делянка ", SQUARE)
    assert f.name == "Моя делянка" and f.owner_id == U4
    with pytest.raises(BusinessRuleError):
        service.create_field(U4, "моя делянка", SQUARE)                    
    with pytest.raises(InvalidValueError):
        service.create_field(U4, "", SQUARE)
    with pytest.raises(InvalidValueError):
        service.create_field(U4, "Плохая геометрия", "not json")
    with pytest.raises(InvalidValueError):
        service.create_field(U4, "Точка", json.dumps({"type": "Point", "coordinates": [1, 2]}))
    with pytest.raises(InvalidValueError):
        service.create_field(U4, "Незамкнутое", json.dumps(
            {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]}))


def test_field_limit(service):
    for i in range(10):
        service.create_field(U4, f"Поле {i}", SQUARE)
    with pytest.raises(BusinessRuleError):
        service.create_field(U4, "Одиннадцатое", SQUARE)


def test_record_measurement_creates_alert_on_drop(service):
    service.record_measurement(F2, 0.50, datetime(2026, 1, 20, 10, 0))  
    alerts = service.list_alerts(F2)
    assert len(alerts) == 1 and alerts[0].type == "NDVI_DROP" and "30%" in alerts[0].message
    service.record_measurement(F2, 0.49, datetime(2026, 1, 21, 10, 0))        
    assert len(service.list_alerts(F2)) == 1


def test_record_measurement_rules(service):
    with pytest.raises(InvalidValueError):
        service.record_measurement(F1, 1.5)
    with pytest.raises(BusinessRuleError):
        service.record_measurement(F1, 0.6, datetime(2026, 1, 1))              
    with pytest.raises(NotFoundError):
        service.record_measurement(str(sid("fld-999")), 0.5)
