import copy
import re
from typing import Optional

from ..errors import BusinessRuleError, NotFoundError, PermissionDeniedError, ValidationError
from .base import AuthClientBase
from .common import check_sort, count_by, new_id, now_iso, paginate

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LANGUAGES = {"ru", "en", "be"}
ROLES = {"CLIENT", "EXPERT", "ADMIN"}
STATUSES = {"ACTIVE", "BLOCKED", "PENDING"}

MOCK_USERS = {
    "user-1": {"id": "user-1", "email": "anna@example.com", "name": "Анна Петрова", "role": "CLIENT",
               "status": "ACTIVE", "created_at": "2026-01-10T09:00:00Z",
               "profile": {"id": "profile-1", "photo_url": None, "description": "Владелица теплицы",
                           "rating": 0.0, "language": "ru"}},
    "user-2": {"id": "user-2", "email": "ivan.expert@example.com", "name": "Иван Сидоров", "role": "EXPERT",
               "status": "ACTIVE", "created_at": "2026-01-05T12:00:00Z",
               "profile": {"id": "profile-2", "photo_url": None, "description": "Агроном-фитопатолог, 10 лет опыта",
                           "rating": 4.8, "language": "ru"}},
    "user-3": {"id": "user-3", "email": "admin@example.com", "name": "Мария Админова", "role": "ADMIN",
               "status": "ACTIVE", "created_at": "2026-01-01T08:00:00Z",
               "profile": {"id": "profile-3", "photo_url": None, "description": "Администратор платформы",
                           "rating": 0.0, "language": "ru"}},
    "user-4": {"id": "user-4", "email": "petr@example.com", "name": "Пётр Огородников", "role": "CLIENT",
               "status": "ACTIVE", "created_at": "2026-01-12T15:30:00Z",
               "profile": {"id": "profile-4", "photo_url": None, "description": "Садовод-любитель",
                           "rating": 0.0, "language": "ru"}},
    "user-5": {"id": "user-5", "email": "oleg@example.com", "name": "Олег Заблокированный", "role": "CLIENT",
               "status": "BLOCKED", "created_at": "2026-01-08T10:00:00Z", "profile": None},
}


class MockAuthClient(AuthClientBase):
    #Mock Auth Service

    def __init__(self):
        self.users = copy.deepcopy(MOCK_USERS)
        self.passwords = {u["email"]: "password123" for u in self.users.values()}

    def get_user(self, user_id: str) -> dict:
        user = self.users.get(user_id)
        if not user:
            raise NotFoundError(f"Пользователь {user_id} не найден")
        return user

    def list_users(self, role=None, status=None, search=None, sort_by="created_at", descending=False,
                   limit=None, offset=0) -> list[dict]:
        check_sort(sort_by, {"created_at", "name", "email"})
        users = list(self.users.values())
        if role:
            users = [u for u in users if u["role"] == role]
        if status:
            users = [u for u in users if u["status"] == status]
        if search:
            needle = search.lower()
            users = [u for u in users if needle in u["name"].lower() or needle in u["email"].lower()]
        users.sort(key=lambda u: (u[sort_by], u["email"]), reverse=descending)
        return paginate(users, limit, offset)

    def users_summary(self) -> dict:
        users = list(self.users.values())
        return {"total": len(users), "by_role": count_by(users, "role"), "by_status": count_by(users, "status")}

    def validate_user(self, user_id: str) -> dict:
        user = self.users.get(user_id)
        if not user:
            return {"valid": False, "role": None, "status": None}
        return {"valid": user["status"] == "ACTIVE", "role": user["role"], "status": user["status"]}

    def register(self, email: str, password: str, name: str) -> dict:
        email, name = (email or "").strip().lower(), (name or "").strip()
        if not EMAIL_RE.match(email):
            raise ValidationError("Некорректный email")
        if len(password or "") < 8:
            raise ValidationError("Пароль должен содержать не менее 8 символов")
        if not 2 <= len(name) <= 100:
            raise ValidationError("Имя должно содержать от 2 до 100 символов")
        if email in self.passwords:
            raise BusinessRuleError("Пользователь с таким email уже зарегистрирован")
        user_id = new_id("user")
        user = {"id": user_id, "email": email, "name": name, "role": "CLIENT", "status": "ACTIVE",
                "created_at": now_iso(),
                "profile": {"id": new_id("profile"), "photo_url": None, "description": None,
                            "rating": 0.0, "language": "ru"}}
        self.users[user_id] = user
        self.passwords[email] = password
        return user

    def login(self, email: str, password: str) -> dict:
        user = next((u for u in self.users.values() if u["email"] == (email or "").strip().lower()), None)
        if user is None or self.passwords.get(user["email"]) != password:
            raise PermissionDeniedError("Неверный email или пароль")
        if user["status"] != "ACTIVE":
            raise PermissionDeniedError("Учётная запись заблокирована или не активирована")
        return {"token": f"mock-token-{user['id']}", "user": user}

    def update_profile(self, user_id, name=None, photo_url=None, description=None, language=None) -> dict:
        if name is not None and not 2 <= len(name.strip()) <= 100:
            raise ValidationError("Имя должно содержать от 2 до 100 символов")
        if language is not None and language not in LANGUAGES:
            raise ValidationError(f"Язык {language} не поддерживается")
        if photo_url is not None and not photo_url.startswith(("http://", "https://")):
            raise ValidationError("photo_url должен быть ссылкой http(s)")
        user = self.get_user(user_id)
        if user["status"] != "ACTIVE":
            raise PermissionDeniedError("Профиль заблокированного пользователя изменять нельзя")
        if user["profile"] is None:
            user["profile"] = {"id": new_id("profile"), "photo_url": None, "description": None,
                               "rating": 0.0, "language": "ru"}
        if name is not None:
            user["name"] = name.strip()
        for key, value in (("photo_url", photo_url), ("description", description), ("language", language)):
            if value is not None:
                user["profile"][key] = value
        return user

    def assign_role(self, user_id: str, role: str) -> dict:
        if role not in ROLES:
            raise ValidationError(f"Неизвестная роль: {role}")
        user = self.get_user(user_id)
        if user["role"] == "ADMIN":
            raise BusinessRuleError("Роль администратора изменять нельзя")
        user["role"] = role
        return user

    def set_status(self, user_id: str, status: str) -> dict:
        if status not in STATUSES:
            raise ValidationError(f"Неизвестный статус: {status}")
        user = self.get_user(user_id)
        if user["role"] == "ADMIN" and status != "ACTIVE":
            raise BusinessRuleError("Администратора нельзя заблокировать")
        user["status"] = status
        return user
