from .database import init_db
from .seed import seed, sid
from .service import ChatService


def main() -> None:
    init_db()
    print("Тестовые данные добавлены" if seed() else "Тестовые данные уже есть")

    service = ChatService()
    room = service.get_chat_room_by_request(str(sid("req-2")))
    print(f"\nЧат {room.status}, сообщений: {len(service.list_messages(room.id))}")
    for m in service.list_messages(room.id):
        print(f"  {m.sent_at}: {m.text}")
    print("Видеокомнат:", len(service.list_video_rooms(room.id)))


if __name__ == "__main__":
    main()
