from .database import init_db
from .seed import seed, sid
from .service import RequestService


def main() -> None:
    init_db()
    print("Тестовые данные добавлены" if seed() else "Тестовые данные уже есть")

    service = RequestService()
    print("\nОчередь заявок для экспертов:")
    for r in service.list_available_requests():
        print(f"  {r.symptoms} (фото: {len(r.photos)})")

    req = service.get_request(str(sid("req-2")))
    print(f"\nЗаявка req-2: статус {req.status}, AI: {req.ai_prediagnosis}")
    print("Болезнь:", service.get_disease(str(sid("dis-1"))).name)


if __name__ == "__main__":
    main()
