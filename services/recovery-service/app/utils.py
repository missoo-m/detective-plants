import uuid
from typing import Optional

from .errors import InvalidValueError


def parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise InvalidValueError(f"Некорректный идентификатор: {value}")


def fmt_dt(dt) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None
