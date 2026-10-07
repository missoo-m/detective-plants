
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


class ExpertClient(ABC):
    @abstractmethod
    def has_responded(self, request_id: str, expert_id: str) -> bool: ...

    @abstractmethod
    def accept_response(self, request_id: str, expert_id: str) -> None: ...


class StorageClient(ABC):
    @abstractmethod
    def save(self, request_id: str, file_name: str, content: bytes) -> str:
        pass


class AiClient(ABC):
    @abstractmethod
    def prediagnose(self, symptoms: str) -> Optional[str]: ...


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


class MockExpertClient(ExpertClient):
    def __init__(self, responded: Optional[set] = None):
        self.responded = set(responded or set())   
        self.accepted: list = []

    def has_responded(self, request_id: str, expert_id: str) -> bool:
        return (request_id, expert_id) in self.responded

    def accept_response(self, request_id: str, expert_id: str) -> None:
        self.accepted.append((request_id, expert_id))


class MockStorageClient(StorageClient):
    def save(self, request_id: str, file_name: str, content: bytes) -> str:
        return f"https://minio/{request_id}/{uuid.uuid4().hex[:8]}-{file_name}"


class MockAiClient(AiClient):
    RULES = [("налёт", "Мучнистая роса"), ("гниль", "Корневая гниль"), ("пятна", "Пятнистость листьев")]

    def prediagnose(self, symptoms: str) -> Optional[str]:
        text = symptoms.lower()
        for keyword, diagnosis in self.RULES:
            if keyword in text:
                return diagnosis
        return None
