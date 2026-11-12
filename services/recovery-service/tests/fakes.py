import uuid
from abc import ABC, abstractmethod


class RequestClient(ABC):
    @abstractmethod
    def complete_request(self, request_id: str) -> None:
        pass


class NotificationClient(ABC):
    @abstractmethod
    def send(self, user_id: str, notification_type: str, message: str) -> None: ...


class StorageClient(ABC):
    @abstractmethod
    def save(self, folder: str, file_name: str, content: bytes) -> str: ...


class FakeRequestClient(RequestClient):
    def __init__(self):
        self.completed: list = []

    def complete_request(self, request_id: str) -> None:
        self.completed.append(request_id)


class FakeNotificationClient(NotificationClient):
    def __init__(self):
        self.sent: list = []

    def send(self, user_id: str, notification_type: str, message: str) -> None:
        self.sent.append((user_id, notification_type, message))


class FakeStorageClient(StorageClient):
    def save(self, folder: str, file_name: str, content: bytes) -> str:
        return f"https://minio/{folder}/{uuid.uuid4().hex[:8]}-{file_name}"


def outbox(factory, event_type=None):
    import json
    from app.models import OutboxEvent
    with factory() as session:
        rows = session.query(OutboxEvent).order_by(OutboxEvent.seq).all()
    events = [json.loads(r.body) for r in rows]
    return [e for e in events if event_type in (None, e["event_type"])]
