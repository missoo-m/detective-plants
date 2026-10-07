import uuid
from abc import ABC, abstractmethod
from typing import Optional

from .errors import NotFoundError


def _sid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"plant-detective/{name}"))


class AuthClient(ABC):
    @abstractmethod
    def get_user(self, user_id: str) -> dict:
        pass


class RequestClient(ABC):
    @abstractmethod
    def get_request_details(self, request_id: str) -> dict:
        pass

    @abstractmethod
    def get_disease(self, disease_id: str) -> dict:
        pass


class RecoveryClient(ABC):
    @abstractmethod
    def create_tracker(self, request_id: str, client_id: str, expert_id: str, duration_days: int) -> dict: ...


class MockAuthClient(AuthClient):
    USERS = {
        _sid("user-1"): ("CLIENT", "ACTIVE"), _sid("user-2"): ("EXPERT", "ACTIVE"),
        _sid("user-3"): ("ADMIN", "ACTIVE"), _sid("user-4"): ("CLIENT", "ACTIVE"),
        _sid("user-5"): ("CLIENT", "BLOCKED"),
    }

    def __init__(self, users: Optional[dict] = None):
        self.users = dict(users if users is not None else self.USERS)

    def get_user(self, user_id: str) -> dict:
        if user_id not in self.users:
            raise NotFoundError(f"Пользователь {user_id} не найден")
        role, status = self.users[user_id]
        return {"id": user_id, "role": role, "status": status}


class MockRequestClient(RequestClient):
    def __init__(self, requests: Optional[dict] = None, diseases: Optional[dict] = None):
        self.requests = requests if requests is not None else {
            _sid("req-1"): {"id": _sid("req-1"), "client_id": _sid("user-1"), "expert_id": None,
                            "status": "CREATED", "ai_prediagnosis": "Возможно мучнистая роса"},
            _sid("req-2"): {"id": _sid("req-2"), "client_id": _sid("user-1"), "expert_id": _sid("user-2"),
                            "status": "IN_PROGRESS", "ai_prediagnosis": "Мучнистая роса"},
            _sid("req-3"): {"id": _sid("req-3"), "client_id": _sid("user-4"), "expert_id": None,
                            "status": "CREATED", "ai_prediagnosis": None},
        }
        self.diseases = diseases if diseases is not None else {
            _sid("dis-1"): {"id": _sid("dis-1"), "name": "Мучнистая роса"},
            _sid("dis-2"): {"id": _sid("dis-2"), "name": "Корневая гниль"},
        }

    def get_request_details(self, request_id: str) -> dict:
        if request_id not in self.requests:
            raise NotFoundError(f"Заявка {request_id} не найдена")
        return self.requests[request_id]

    def get_disease(self, disease_id: str) -> dict:
        if disease_id not in self.diseases:
            raise NotFoundError(f"Болезнь {disease_id} не найдена")
        return self.diseases[disease_id]


class MockRecoveryClient(RecoveryClient):
    def __init__(self):
        self.created: list = []

    def create_tracker(self, request_id: str, client_id: str, expert_id: str, duration_days: int) -> dict:
        self.created.append((request_id, client_id, expert_id, duration_days))
        return {"request_id": request_id, "duration_days": duration_days}
