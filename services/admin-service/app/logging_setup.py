import contextvars
import json
import logging
import os
import sys
import time
import uuid
from typing import Optional

CORRELATION_HEADER = "x-correlation-id"
correlation_id: contextvars.ContextVar = contextvars.ContextVar("correlation_id", default="-")
deadline_at: contextvars.ContextVar = contextvars.ContextVar("deadline_at", default=None)


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:16]


def remaining_budget() -> Optional[float]:
    limit = deadline_at.get()
    return None if limit is None else limit - time.monotonic()


class ContextFilter(logging.Filter):

    def __init__(self, service: str):
        super().__init__()
        self._service = service

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id.get()
        record.service = self._service
        return True


class JsonFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        data = {"time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S") + f".{int(record.msecs):03d}",
                "level": record.levelname, "service": getattr(record, "service", "-"),
                "correlation_id": getattr(record, "correlation_id", "-"), "logger": record.name,
                "message": record.getMessage()}
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


TEXT_FORMAT = "%(asctime)s %(levelname)-7s [%(service)s] [%(correlation_id)s] %(name)s: %(message)s"


def configure_logging(service: str) -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    context = ContextFilter(service)
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(JsonFormatter() if os.getenv("LOG_FORMAT", "text") == "json" else logging.Formatter(TEXT_FORMAT))
    console.addFilter(context)
    root.addHandler(console)
    directory = os.getenv("LOG_DIR")
    if directory:
        os.makedirs(directory, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(directory, f"{service}.log"), encoding="utf-8")
        file_handler.setFormatter(JsonFormatter())
        file_handler.addFilter(context)
        root.addHandler(file_handler)
    for noisy in ("urllib3", "asyncio", "kafka", "grpc"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
