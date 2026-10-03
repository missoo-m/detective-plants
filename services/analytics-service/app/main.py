from .database import init_db
from .seed import seed, sid
from .service import AnalyticsService


def main() -> None:
    init_db()
    print("Тестовые данные добавлены" if seed() else "Тестовые данные уже есть")

    service = AnalyticsService()
    s = service.get_expert_stats(str(sid("user-2")))
    print(f"\nЭксперт user-2: заявок {s.total_requests}, завершено {s.completed_requests}, рейтинг {s.avg_rating}")
    print("Болезни за 2026-01:", [(d.disease_id[:8], d.count) for d in service.list_disease_stats("2026-01")])


if __name__ == "__main__":
    main()
