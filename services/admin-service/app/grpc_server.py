from .grpc_support import request_args, rpc
from .proto import admin_pb2 as pb, admin_pb2_grpc as pb_grpc
from .utils import parse_dt_bound


class AdminServicer(pb_grpc.AdminServiceServicer):
    def __init__(self, service):
        self.s = service

    @rpc(pb.ApplicationResponse)
    def SubmitApplication(self, request, context):
        return self.s.submit_application(**request_args(request))

    @rpc(pb.ApplicationResponse)
    def VerifyExpert(self, request, context):
        return self.s.verify_expert(**request_args(request))

    @rpc(pb.BlockUserResponse)
    def BlockUser(self, request, context):
        return self.s.block_user(**request_args(request))

    @rpc(pb.ListApplicationsResponse)
    def ListApplications(self, request, context):
        args = request_args(request)
        args["submitted_from"] = parse_dt_bound(args.get("submitted_from"))
        args["submitted_to"] = parse_dt_bound(args.get("submitted_to"), upper=True)
        return {"applications": self.s.list_applications(**args)}

    @rpc(pb.ApplicationsSummaryResponse)
    def GetApplicationsSummary(self, request, context):
        return self.s.applications_summary()


def registration(service):
    servicer = AdminServicer(service)
    return ([lambda server: pb_grpc.add_AdminServiceServicer_to_server(servicer, server)],
            [pb.DESCRIPTOR.services_by_name["AdminService"].full_name])
