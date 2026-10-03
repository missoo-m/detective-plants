import hashlib
import uuid
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session_factory
from .models import Profile, ReferralProfile, Role, User, UserSettings


def sid(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"plant-detective/{name}")


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


USERS = [
    ("user-1", "anna@example.com", "Анна Петрова", "CLIENT", "ACTIVE",
     datetime(2026, 1, 10, 9, 0), 0.0, "Владелица теплицы"),
    ("user-2", "ivan.expert@example.com", "Иван Сидоров", "EXPERT", "ACTIVE",
     datetime(2026, 1, 5, 12, 0), 4.8, "Агроном-фитопатолог, 10 лет опыта"),
    ("user-3", "admin@example.com", "Мария Админова", "ADMIN", "ACTIVE",
     datetime(2026, 1, 1, 8, 0), 0.0, "Администратор платформы"),
    ("user-4", "petr@example.com", "Пётр Огородников", "CLIENT", "ACTIVE",
     datetime(2026, 1, 12, 15, 30), 0.0, "Садовод-любитель"),
    ("user-5", "oleg@example.com", "Олег Заблокированный", "CLIENT", "BLOCKED",
     datetime(2026, 1, 8, 10, 0), 0.0, None),
]


def seed(session_factory: Optional[Callable[[], Session]] = None) -> bool:
    factory = session_factory or get_session_factory()
    with factory() as session:
        if session.scalars(select(Role)).first():
            return False

        roles = {}
        for name, desc in [("CLIENT", "Владелец растений"),
                           ("EXPERT", "Агроном / фитопатолог"),
                           ("ADMIN", "Администратор системы")]:
            role = Role(id=sid(f"role-{name}"), name=name, description=desc)
            roles[name] = role
            session.add(role)
        session.flush()

        for key, email, name, role, status, created, rating, desc in USERS:
            user = User(
                id=sid(key), email=email, name=name, role_id=roles[role].id,
                password_hash=_hash("password123"), status=status, created_at=created,
            )
            session.add(user)
            session.flush()
            session.add(Profile(id=sid(f"profile-{key}"), user_id=user.id,
                                description=desc, rating=rating, language="ru"))
            session.add(UserSettings(id=sid(f"settings-{key}"), user_id=user.id,
                                     language="ru", theme="light", notifications_enabled=True))

        session.add(ReferralProfile(id=sid("referral-user-1"), user_id=sid("user-1"),
                                    referral_link="https://detective-plants.example/ref/anna",
                                    invited_count=2, bonus_balance=10.0))
        session.commit()
        return True
