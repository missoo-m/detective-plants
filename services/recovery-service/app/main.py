from .database import init_db
from .seed import seed, sid
from .service import RecoveryService


def main() -> None:
    init_db()
    print("Тестовые данные добавлены" if seed() else "Тестовые данные уже есть")

    tracker = RecoveryService().get_tracker_by_request(str(sid("req-2")))
    print(f"\nТрекер {tracker.status}, этап {tracker.current_stage}, записей истории: {len(tracker.history)}")
    for h in tracker.history:
        print(f"  [{h.record_type}] {h.change_description or h.photo_url}")


if __name__ == "__main__":
    main()
