from typing import Optional
from .base import AuthClientBase, NotFoundError

MOCK_USERS = {
    "user-1": {
        "id": "user-1", "email": "anna@example.com", "name": "Анна Петрова",
        "role": "CLIENT", "status": "ACTIVE", "created_at": "2026-01-10T09:00:00Z",
        "profile": {"id": "profile-1", "photo_url": None, "description": "Владелица теплицы",
                    "rating": 0.0, "language": "ru"},
    },
    "user-2": {
        "id": "user-2", "email": "ivan.expert@example.com", "name": "Иван Сидоров",
        "role": "EXPERT", "status": "ACTIVE", "created_at": "2026-01-05T12:00:00Z",
        "profile": {"id": "profile-2", "photo_url": None,
                    "description": "Агроном-фитопатолог, 10 лет опыта",
                    "rating": 4.8, "language": "ru"},
    },
    "user-3": {
        "id": "user-3", "email": "admin@example.com", "name": "Мария Админова",
        "role": "ADMIN", "status": "ACTIVE", "created_at": "2026-01-01T08:00:00Z",
        "profile": {"id": "profile-3", "photo_url": None, "description": "Администратор платформы",
                    "rating": 0.0, "language": "ru"},
    },
    "user-4": {
        "id": "user-4", "email": "petr@example.com", "name": "Пётр Огородников",
        "role": "CLIENT", "status": "ACTIVE", "created_at": "2026-01-12T15:30:00Z",
        "profile": {"id": "profile-4", "photo_url": None, "description": "Садовод-любитель",
                    "rating": 0.0, "language": "ru"},
    },
    "user-5": {
        "id": "user-5", "email": "oleg@example.com", "name": "Олег Заблокированный",
        "role": "CLIENT", "status": "BLOCKED", "created_at": "2026-01-08T10:00:00Z",
        "profile": None,
    },
}


class MockAuthClient(AuthClientBase):
    #Mock-клиент Auth Service

    def get_user(self, user_id: str) -> dict:
        user = MOCK_USERS.get(user_id)
        if not user:
            raise NotFoundError(f"Пользователь {user_id} не найден")
        return user

    def list_users(self, role: Optional[str] = None, status: Optional[str] = None) -> list[dict]:
        users = list(MOCK_USERS.values())
        if role:
            users = [u for u in users if u["role"] == role]
        if status:
            users = [u for u in users if u["status"] == status]
        return users

    def validate_user(self, user_id: str) -> dict:
        user = MOCK_USERS.get(user_id)
        if not user:
            return {"valid": False, "role": None, "status": None}
        return {"valid": user["status"] == "ACTIVE", "role": user["role"], "status": user["status"]}
