import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Field(Base):
    __tablename__ = "fields"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(Uuid(as_uuid=True), nullable=False)       
    name = Column(String(100), nullable=False)
    geometry = Column(Text, nullable=False)                     
    created_at = Column(DateTime, nullable=False, default=utcnow)

    measurements = relationship("NdviMeasurement", back_populates="field",
                                order_by="NdviMeasurement.measured_at", cascade="all, delete-orphan")
    alerts = relationship("SatelliteAlert", back_populates="field",
                          order_by="SatelliteAlert.created_at", cascade="all, delete-orphan")


class NdviMeasurement(Base):
    __tablename__ = "ndvi_measurements"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id = Column(Uuid(as_uuid=True), ForeignKey("fields.id"), nullable=False)
    ndvi_value = Column(Float, nullable=False)
    measured_at = Column(DateTime, nullable=False)

    field = relationship("Field", back_populates="measurements")


class SatelliteAlert(Base):
    __tablename__ = "satellite_alerts"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id = Column(Uuid(as_uuid=True), ForeignKey("fields.id"), nullable=False)
    type = Column(String(50), nullable=False)                   
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    field = relationship("Field", back_populates="alerts")
