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


def parse_dt_bound(value: Optional[str], upper: bool = False):
    if not value:
        return None
    from datetime import datetime
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise InvalidValueError(f"Некорректная дата: {value} (ожидается формат ISO 8601)")
    return moment.replace(hour=23, minute=59, second=59) if upper and len(value) == 10 else moment
