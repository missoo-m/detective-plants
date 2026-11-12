import pytest

pytest.importorskip("grpc")
pb = pytest.importorskip("app.proto.chat_pb2")
pb_grpc = pytest.importorskip("app.proto.chat_pb2_grpc")

from app.seed import sid
from tests.helpers import make_factory, serve
from app.service import ChatService

@pytest.fixture
def api():
    service = ChatService(make_factory())
    with serve(service, "ChatServiceStub", pb_grpc) as (stub, channel):
        yield stub, channel, service


R2, R3 = str(sid("req-2")), str(sid("req-3"))
U1 = str(sid("user-1"))


def test_room_lookup(api):
    stub, channel, _ = api
    found = channel.call(stub.GetChatRoomByRequest, pb.GetChatRoomByRequestRequest(request_id=R2, viewer_id=U1))
    assert found.found and found.room.request_id == R2
    assert channel.call(stub.GetChatRoomByRequest, pb.GetChatRoomByRequestRequest(request_id=R3)).found is False


def test_send_and_list_messages(api):
    stub, channel, _ = api
    room = channel.call(stub.GetChatRoomByRequest, pb.GetChatRoomByRequestRequest(request_id=R2)).room
    sent = channel.call(stub.SendMessage, pb.SendMessageRequest(chat_room_id=room.id, sender_id=U1, text="Новое фото"))
    assert sent.is_read is False
    listed = channel.call(stub.ListMessages, pb.ListMessagesRequest(chat_room_id=room.id, descending=True, limit=1))
    assert listed.messages[0].id == sent.id
