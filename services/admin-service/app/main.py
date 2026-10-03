
from .database import init_db
from .seed import seed
from .service import AdminService


def main() -> None:
    init_db()
    print("Тестовые данные добавлены" if seed() else "Тестовые данные уже есть")

    service = AdminService()
    print("\nЗаявки на статус эксперта, ожидающие проверки:")
    for a in service.list_applications(status="PENDING"):
        print(f"  {a.documents_url} (подана {a.submitted_at})")


if __name__ == "__main__":
    main()
