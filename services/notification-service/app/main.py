from .database import init_db
from .seed import seed, sid
from .service import NotificationService


def main() -> None:
    init_db()
    print("Тестовые данные добавлены" if seed() else "Тестовые данные уже есть")

    service = NotificationService()
    user = str(sid("user-1"))
    print(f"\nНепрочитанных у user-1: {service.count_unread(user)}")
    for n in service.list_notifications(user):
        print(f"  [{n.status}] {n.message}")


if __name__ == "__main__":
    main()
