from .database import init_db
from .seed import seed, sid
from .service import ExpertService


def main() -> None:
    init_db()
    print("Тестовые данные добавлены" if seed() else "Тестовые данные уже есть")

    service = ExpertService()
    print("\nОтклики на заявку req-1:")
    for r in service.list_responses(str(sid("req-1"))):
        print(f"  [{r.status}] {r.comment}")

    d = service.get_diagnosis_by_request(str(sid("req-2")))
    print(f"\nДиагноз по заявке req-2: {d.description}")
    for i, step in enumerate(d.checklist, 1):
        print(f"  {i}. {step.step} ({step.frequency})")


if __name__ == "__main__":
    main()
