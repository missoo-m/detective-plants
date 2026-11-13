from .grpc_support import request_args, rpc
from .proto import expert_pb2 as pb, expert_pb2_grpc as pb_grpc


class ExpertServicer(pb_grpc.ExpertServiceServicer):
    def __init__(self, service):
        self.s = service

    @rpc(pb.ExpertResponseMsg)
    def RespondToRequest(self, request, context):
        return self.s.respond_to_request(**request_args(request))

    @rpc(pb.DiagnosisResponse)
    def CreateDiagnosis(self, request, context):
        return self.s.create_diagnosis(**request_args(request))

    @rpc(pb.DiagnosisResponse)
    def GetDiagnosis(self, request, context):
        return self.s.get_diagnosis_by_request(request.request_id)

    @rpc(pb.DiagnosisResponse)
    def GetDiagnosisById(self, request, context):
        return self.s.get_diagnosis(request.diagnosis_id)

    @rpc(pb.TreatmentStepResponse)
    def AddTreatmentStep(self, request, context):
        return self.s.add_treatment_step(**request_args(request))

    @rpc(pb.ListResponsesResponse)
    def ListResponses(self, request, context):
        return {"responses": self.s.list_responses(request.request_id)}

    @rpc(pb.ResponsesSummaryResponse)
    def GetResponsesSummary(self, request, context):
        return self.s.responses_summary(request.expert_id)


def registration(service):
    servicer = ExpertServicer(service)
    return ([lambda server: pb_grpc.add_ExpertServiceServicer_to_server(servicer, server)],
            [pb.DESCRIPTOR.services_by_name["ExpertService"].full_name])
