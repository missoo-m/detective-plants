from .grpc_support import request_args, rpc
from .proto import notification_pb2 as pb, notification_pb2_grpc as pb_grpc


class NotificationServicer(pb_grpc.NotificationServiceServicer):
    def __init__(self, service):
        self.s = service

    @rpc(pb.NotificationResponse)
    def SendNotification(self, request, context):
        return self.s.create_notification(request.user_id, request.type, request.message)

    @rpc(pb.ListNotificationsResponse)
    def ListNotifications(self, request, context):
        return {"notifications": self.s.list_notifications(**request_args(request))}

    @rpc(pb.NotificationsSummaryResponse)
    def GetNotificationsSummary(self, request, context):
        return self.s.notifications_summary(request.user_id)

    @rpc(pb.NotificationResponse)
    def MarkRead(self, request, context):
        return self.s.mark_read(request.notification_id, request.user_id)

    @rpc(pb.MarkAllReadResponse)
    def MarkAllRead(self, request, context):
        return {"count": self.s.mark_all_read(request.user_id)}


def registration(service):
    servicer = NotificationServicer(service)
    return ([lambda server: pb_grpc.add_NotificationServiceServicer_to_server(servicer, server)],
            [pb.DESCRIPTOR.services_by_name["NotificationService"].full_name])
