from .grpc_support import request_args, rpc
from .proto import request_pb2 as pb, request_pb2_grpc as pb_grpc
from .utils import parse_dt_bound


class RequestServicer(pb_grpc.RequestServiceServicer):
    def __init__(self, service):
        self.s = service

    @staticmethod
    def _list_args(request) -> dict:
        args = request_args(request)
        args["created_from"] = parse_dt_bound(args.get("created_from"))
        args["created_to"] = parse_dt_bound(args.get("created_to"), upper=True)
        return args

    @rpc(pb.RequestResponse)
    def CreateRequest(self, request, context):
        return self.s.create_request(request.client_id, request.symptoms, list(request.photo_urls),
                                     request.actor_role if request.HasField("actor_role") else None)

    @rpc(pb.RequestResponse)
    def GetRequest(self, request, context):
        return self.s.get_request(request.request_id)

    @rpc(pb.RequestDetailsResponse)
    def GetRequestDetails(self, request, context):
        return self.s.get_request_details(request.request_id)

    @rpc(pb.ListRequestsResponse)
    def ListRequests(self, request, context):
        return {"requests": self.s.list_requests(**self._list_args(request))}

    @rpc(pb.ListRequestsResponse)
    def ListAvailableRequests(self, request, context):
        return {"requests": self.s.list_available_requests(**self._list_args(request))}

    @rpc(pb.RequestsSummaryResponse)
    def GetRequestsSummary(self, request, context):
        return self.s.requests_summary(**request_args(request))

    @rpc(pb.RequestResponse)
    def SelectExpert(self, request, context):
        return self.s.select_expert(request.request_id, request.client_id, request.expert_id)

    @rpc(pb.RequestResponse)
    def CancelRequest(self, request, context):
        return self.s.cancel_request(request.request_id, request.client_id)

    @rpc(pb.PhotoResponse)
    def AddPhoto(self, request, context):
        return self.s.add_photo(request.request_id, request.client_id, request.file_name, request.content)

    @rpc(pb.DiseaseResponse)
    def GetDisease(self, request, context):
        return self.s.get_disease(request.disease_id)

    @rpc(pb.ListDiseasesResponse)
    def ListDiseases(self, request, context):
        return {"diseases": self.s.list_diseases()}


def registration(service):
    servicer = RequestServicer(service)
    return ([lambda server: pb_grpc.add_RequestServiceServicer_to_server(servicer, server)],
            [pb.DESCRIPTOR.services_by_name["RequestService"].full_name])
