from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session_factory
from .models import Field, NdviMeasurement, SatelliteAlert

import uuid


def sid(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"plant-detective/{name}")


SQUARE = '{"type": "Polygon", "coordinates": [[[27.55, 53.90], [27.56, 53.90], [27.56, 53.91], [27.55, 53.91], [27.55, 53.90]]]}'


def seed(session_factory: Optional[Callable[[], Session]] = None) -> bool:
    factory = session_factory or get_session_factory()
    with factory() as session:
        if session.scalars(select(Field)).first():
            return False
        f1 = Field(id=sid("fld-1"), owner_id=sid("user-1"), name="Теплица №1", geometry=SQUARE,
                   created_at=datetime(2026, 1, 10, 12, 0))
        f1.measurements = [
            NdviMeasurement(id=sid("ndvi-1"), ndvi_value=0.62, measured_at=datetime(2026, 1, 10, 10, 0)),
            NdviMeasurement(id=sid("ndvi-2"), ndvi_value=0.55, measured_at=datetime(2026, 1, 17, 10, 0)),
        ]
        f1.alerts = [SatelliteAlert(id=sid("alert-1"), type="NDVI_DROP",
                                    message="Снижение NDVI на 11% за неделю",
                                    created_at=datetime(2026, 1, 17, 12, 0))]
        f2 = Field(id=sid("fld-2"), owner_id=sid("user-1"), name="Огород у дома", geometry=SQUARE,
                   created_at=datetime(2026, 1, 11, 9, 0))
        f2.measurements = [NdviMeasurement(id=sid("ndvi-3"), ndvi_value=0.71, measured_at=datetime(2026, 1, 12, 10, 0))]
        session.add_all([f1, f2])
        session.commit()
        return True
