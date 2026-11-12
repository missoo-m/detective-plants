from .grpc_support import request_args, rpc
from .proto import analytics_pb2 as pb, analytics_pb2_grpc as pb_grpc


class AnalyticsServicer(pb_grpc.AnalyticsServiceServicer):
    def __init__(self, service):
        self.s = service

    @rpc(pb.ExpertStatsResponse)
    def GetExpertStats(self, request, context):
        return self.s.get_expert_stats(request.expert_id)

    @rpc(pb.TopExpertsResponse)
    def GetTopExperts(self, request, context):
        return {"experts": self.s.top_experts(**request_args(request))}

    @rpc(pb.DiseaseStatsResponse)
    def GetDiseaseStats(self, request, context):
        return {"items": self.s.list_disease_stats(**request_args(request))}

    @rpc(pb.PlatformSummaryResponse)
    def GetPlatformSummary(self, request, context):
        return self.s.platform_summary()

    @rpc(pb.EventCountersResponse)
    def GetEventCounters(self, request, context):
        return {"counters": self.s.event_counters(**request_args(request))}


def registration(service):
    servicer = AnalyticsServicer(service)
    return ([lambda server: pb_grpc.add_AnalyticsServiceServicer_to_server(servicer, server)],
            [pb.DESCRIPTOR.services_by_name["AnalyticsService"].full_name])
