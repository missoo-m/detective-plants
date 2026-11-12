import uuid
from abc import ABC, abstractmethod
from typing import Optional

from app.errors import NotFoundError


def _sid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"plant-detective/{name}"))


class AuthClient(ABC):
    @abstractmethod
    def get_user(self, user_id: str) -> dict:
        pass

    @abstractmethod
    def assign_role(self, user_id: str, role: str) -> None:
        pass

    @abstractmethod
    def set_status(self, user_id: str, status: str) -> None:
        pass


class FakeAuthClient(AuthClient):
    USERS = {
        _sid("user-1"): ("CLIENT", "ACTIVE"), _sid("user-2"): ("EXPERT", "ACTIVE"),
        _sid("user-3"): ("ADMIN", "ACTIVE"), _sid("user-4"): ("CLIENT", "ACTIVE"),
        _sid("user-5"): ("CLIENT", "BLOCKED"),
    }

    def __init__(self, users: Optional[dict] = None):
        self.users = {k: list(v) for k, v in (users if users is not None else self.USERS).items()}

    def get_user(self, user_id: str) -> dict:
        if user_id not in self.users:
            raise NotFoundError(f"Пользователь {user_id} не найден")
        role, status = self.users[user_id]
        return {"id": user_id, "role": role, "status": status}

    def assign_role(self, user_id: str, role: str) -> None:
        self.get_user(user_id)
        self.users[user_id][0] = role

    def set_status(self, user_id: str, status: str) -> None:
        self.get_user(user_id)
        self.users[user_id][1] = status


def outbox(factory, event_type=None):
    import json
    from app.models import OutboxEvent
    with factory() as session:
        rows = session.query(OutboxEvent).order_by(OutboxEvent.seq).all()
    events = [json.loads(r.body) for r in rows]
    return [e for e in events if event_type in (None, e["event_type"])]
