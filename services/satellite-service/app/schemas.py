from dataclasses import dataclass


@dataclass
class FieldDTO:
    id: str
    owner_id: str
    name: str
    geometry: str
    created_at: str


@dataclass
class MeasurementDTO:
    id: str
    field_id: str
    ndvi_value: float
    measured_at: str


@dataclass
class AlertDTO:
    id: str
    field_id: str
    type: str
    message: str
    created_at: str


@dataclass
class NdviSummaryDTO:
    field_id: str
    count: int
    min_value: float
    max_value: float
    avg_value: float
    last_value: float
    trend: float            
