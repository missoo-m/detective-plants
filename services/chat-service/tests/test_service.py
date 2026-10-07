import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from app.models import Base, ModerationRule
from app.seed import seed, sid
from app.service import ChatService

U1, U2, U4 = (str(sid(f"user-{i}")) for i in (1, 2, 4))
R1, R2 = str(sid("req-1")), str(sid("req-2"))
CHAT = str(sid("chat-1"))


@pytest.fixture
def factory():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    f = sessionmaker(bind=engine, expire_on_commit=False)
    assert seed(f) is True
    assert seed(f) is False
    return f


@pytest.fixture
def service(factory):
    return ChatService(factory)


def test_reads_and_access(service):
    room = service.get_chat_room_by_request(R2, viewer_id=U1)
    assert room.status == "ACTIVE" and service.get_chat_room(room.id).id == CHAT
    with pytest.raises(PermissionDeniedError):
        service.get_chat_room(CHAT, viewer_id=U4)                       # посторонний
    with pytest.raises(NotFoundError):
        service.get_chat_room_by_request(R1)
    assert len(service.list_video_rooms(CHAT)) == 1 and len(service.list_moderation_rules()) == 1


def test_messages_filter_sort_aggregate(service):
    assert len(service.list_messages(CHAT)) == 3
    assert service.list_messages(CHAT, descending=True, limit=1)[0].text == "Спасибо за диагноз!"
    assert len(service.list_messages(CHAT, sender_id=U2)) == 1
    assert [m.text for m in service.list_messages(CHAT, unread_only=True)] == ["Спасибо за диагноз!"]
    assert len(service.list_messages(CHAT, search="фото")) == 1
    assert service.unread_count(CHAT, U2) == 1 and service.unread_count(CHAT, U1) == 0
    with pytest.raises(InvalidValueError):
        service.list_messages(CHAT, limit=0)


def test_open_room_is_idempotent(service):
    first = service.open_room(R1, U1, U2)
    assert first.status == "ACTIVE" and service.open_room(R1, U1, U2).id == first.id


def test_send_message(service):
    m = service.send_message(CHAT, U2, "  Продолжайте обработку  ")
    assert m.text == "Продолжайте обработку" and m.is_read is False
    assert service.send_message(CHAT, U1, attachment_url="https://minio/a.jpg").text is None
    with pytest.raises(InvalidValueError):
        service.send_message(CHAT, U1, "  ")
    with pytest.raises(InvalidValueError):
        service.send_message(CHAT, U1, "x" * 2001)
    with pytest.raises(PermissionDeniedError):
        service.send_message(CHAT, U4, "Я посторонний")


def test_closed_room(service, factory):
    from app.models import ChatRoom
    with factory() as s:
        s.get(ChatRoom, sid("chat-1")).status = "CLOSED"
        s.commit()
    with pytest.raises(BusinessRuleError):
        service.send_message(CHAT, U1, "Сообщение в закрытый чат")
    with pytest.raises(BusinessRuleError):
        service.create_video_room(CHAT, U2)


def test_moderation_block_and_warn(service, factory):
    with factory() as s:
        s.add(ModerationRule(name="Запрещённое слово", pattern=r"казино", action="BLOCK"))
        s.commit()
    with pytest.raises(BusinessRuleError):
        service.send_message(CHAT, U1, "Заходите в казино")
    assert len(service.list_messages(CHAT)) == 3                          # заблокированное не сохранено
    warned = service.send_message(CHAT, U1, "Звоните +375 29 123 45 67")   # правило WARN: сообщение проходит
    assert warned.text.startswith("Звоните")


def test_mark_read(service):
    msg = service.list_messages(CHAT, unread_only=True)[0]
    with pytest.raises(BusinessRuleError):
        service.mark_read(msg.id, U1)                                     # автор
    with pytest.raises(PermissionDeniedError):
        service.mark_read(msg.id, U4)
    assert service.mark_read(msg.id, U2).is_read is True and service.unread_count(CHAT, U2) == 0


def test_video_room(service):
    with pytest.raises(PermissionDeniedError):
        service.create_video_room(CHAT, U1)                               # только эксперт
    video = service.create_video_room(CHAT, U2)                           # предыдущая FINISHED
    assert video.status == "CREATED" and video.room_url.endswith(video.id)
    with pytest.raises(BusinessRuleError):
        service.create_video_room(CHAT, U2)                               # прошлая ещё не завершена
