from .database import init_db
from .seed import seed, sid
from .service import PaymentService


def main() -> None:
    init_db()
    print("Тестовые данные добавлены" if seed() else "Тестовые данные уже есть")

    service = PaymentService()
    print("\nТранзакции по заявке req-2:")
    for t in service.list_transactions(request_id=str(sid("req-2"))):
        print(f"  {t.operation_type} {t.amount:.2f} [{t.status}]")
    print("Заявки на вывод:", [(w.amount, w.status) for w in service.list_withdrawals()])


if __name__ == "__main__":
    main()
