import pytest

pytest.importorskip("grpc")
pb = pytest.importorskip("app.proto.satellite_pb2")
pb_grpc = pytest.importorskip("app.proto.satellite_pb2_grpc")

from app.errors import NotFoundError
from app.seed import sid
from tests.helpers import make_factory, serve
from app.service import SatelliteService

@pytest.fixture
def api():
    service = SatelliteService(make_factory())
    with serve(service, "SatelliteServiceStub", pb_grpc) as (stub, channel):
        yield stub, channel, service


F2 = str(sid("fld-2"))
U1 = str(sid("user-1"))


def test_record_measurement_creates_alert(api):
    stub, channel, _ = api
    channel.call(stub.RecordMeasurement, pb.RecordMeasurementRequest(field_id=F2, ndvi_value=0.5, measured_at="2026-01-20T10:00:00"))
    alerts = channel.call(stub.ListAlerts, pb.ListAlertsRequest(owner_id=U1, alert_type="NDVI_DROP"))
    assert any("30%" in a.message for a in alerts.alerts)
    summary = channel.call(stub.GetNdviSummary, pb.GetFieldRequest(field_id=F2))
    assert summary.last_value == 0.5 and summary.count >= 2


def test_unknown_field(api):
    stub, channel, _ = api
    with pytest.raises(NotFoundError):
        channel.call(stub.GetField, pb.GetFieldRequest(field_id=str(sid("fld-404"))))
