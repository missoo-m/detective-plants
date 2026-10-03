from .database import init_db
from .seed import seed, sid
from .service import AuthService


def main() -> None:
    init_db()
    print("Тестовые данные добавлены" if seed() else "Тестовые данные уже есть")

    service = AuthService()
    print("\nЭксперты:")
    for u in service.list_users(role="EXPERT"):
        print(f"  {u.name} <{u.email}> рейтинг={u.profile.rating if u.profile else '-'}")

    user = service.get_user(str(sid("user-1")))
    print(f"\nПользователь user-1: {user.name}, роль {user.role}, статус {user.status}")
    print("validate_user(user-5):", service.validate_user(str(sid("user-5"))))


if __name__ == "__main__":
    main()
