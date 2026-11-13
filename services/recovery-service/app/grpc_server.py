from .errors import NotFoundError
from .grpc_support import request_args, rpc
from .proto import recovery_pb2 as pb, recovery_pb2_grpc as pb_grpc


class RecoveryServicer(pb_grpc.RecoveryServiceServicer):
    def __init__(self, service):
        self.s = service

    @rpc(pb.TrackerResponse)
    def GetTracker(self, request, context):
        return self.s.get_tracker(request.tracker_id)

    @rpc(pb.TrackerLookupResponse)
    def GetTrackerByRequest(self, request, context):
        try:
            return {"found": True, "tracker": self.s.get_tracker_by_request(request.request_id)}
        except NotFoundError:
            return {"found": False}

    @rpc(pb.ProgressResponse)
    def GetTrackerProgress(self, request, context):
        return self.s.tracker_progress(request.tracker_id)

    @rpc(pb.HistoryResponse)
    def UploadPhoto(self, request, context):
        return self.s.upload_photo(request.tracker_id, request.author_id, request.file_name, request.content)

    @rpc(pb.HistoryResponse)
    def UpdateTreatment(self, request, context):
        return self.s.update_treatment(**request_args(request))

    @rpc(pb.TrackerResponse)
    def CompleteTracker(self, request, context):
        return self.s.complete_tracker(request.tracker_id, request.expert_id)


def registration(service):
    servicer = RecoveryServicer(service)
    return ([lambda server: pb_grpc.add_RecoveryServiceServicer_to_server(servicer, server)],
            [pb.DESCRIPTOR.services_by_name["RecoveryService"].full_name])
