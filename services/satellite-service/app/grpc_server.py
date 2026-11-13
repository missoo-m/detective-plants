from datetime import datetime

from .errors import InvalidValueError
from .grpc_support import request_args, rpc
from .proto import satellite_pb2 as pb, satellite_pb2_grpc as pb_grpc


class SatelliteServicer(pb_grpc.SatelliteServiceServicer):
    def __init__(self, service):
        self.s = service

    @rpc(pb.FieldResponse)
    def CreateField(self, request, context):
        return self.s.create_field(request.owner_id, request.name, request.geometry)

    @rpc(pb.FieldResponse)
    def GetField(self, request, context):
        return self.s.get_field(request.field_id)

    @rpc(pb.ListFieldsResponse)
    def ListFields(self, request, context):
        return {"fields": self.s.list_fields(request.owner_id)}

    @rpc(pb.ListMeasurementsResponse)
    def ListMeasurements(self, request, context):
        return {"measurements": self.s.list_measurements(**request_args(request))}

    @rpc(pb.MeasurementResponse)
    def RecordMeasurement(self, request, context):
        when = None
        if request.HasField("measured_at"):
            try:
                when = datetime.fromisoformat(request.measured_at.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                raise InvalidValueError("measured_at должен быть датой в формате ISO 8601")
        return self.s.record_measurement(request.field_id, request.ndvi_value, when)

    @rpc(pb.ListAlertsResponse)
    def ListAlerts(self, request, context):
        return {"alerts": self.s.list_alerts(**request_args(request))}

    @rpc(pb.NdviSummaryResponse)
    def GetNdviSummary(self, request, context):
        return self.s.ndvi_summary(request.field_id)


def registration(service):
    servicer = SatelliteServicer(service)
    return ([lambda server: pb_grpc.add_SatelliteServiceServicer_to_server(servicer, server)],
            [pb.DESCRIPTOR.services_by_name["SatelliteService"].full_name])
