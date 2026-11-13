from .errors import NotFoundError
from .grpc_support import request_args, rpc
from .proto import chat_pb2 as pb, chat_pb2_grpc as pb_grpc


class ChatServicer(pb_grpc.ChatServiceServicer):
    def __init__(self, service):
        self.s = service

    @rpc(pb.MessageResponse)
    def SendMessage(self, request, context):
        return self.s.send_message(**request_args(request))

    @rpc(pb.VideoRoomResponse)
    def CreateVideoRoom(self, request, context):
        return self.s.create_video_room(request.chat_room_id, request.expert_id)

    @rpc(pb.ChatRoomResponse)
    def GetChatRoom(self, request, context):
        return self.s.get_chat_room(**request_args(request))

    @rpc(pb.ChatRoomLookupResponse)
    def GetChatRoomByRequest(self, request, context):
        try:
            return {"found": True, "room": self.s.get_chat_room_by_request(**request_args(request))}
        except NotFoundError:
            return {"found": False}

    @rpc(pb.ListMessagesResponse)
    def ListMessages(self, request, context):
        return {"messages": self.s.list_messages(**request_args(request))}

    @rpc(pb.UnreadCountResponse)
    def GetUnreadCount(self, request, context):
        return {"count": self.s.unread_count(request.chat_room_id, request.user_id)}

    @rpc(pb.MessageResponse)
    def MarkRead(self, request, context):
        return self.s.mark_read(request.message_id, request.reader_id)


def registration(service):
    servicer = ChatServicer(service)
    return ([lambda server: pb_grpc.add_ChatServiceServicer_to_server(servicer, server)],
            [pb.DESCRIPTOR.services_by_name["ChatService"].full_name])
