import uuid
from datetime import datetime, timezone
from typing import Optional

from ..errors import ValidationError


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise ValidationError(f"Некорректная дата: {value} (ожидается формат ISO 8601)")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:6]}"


def lower_bound(value: Optional[str]) -> Optional[datetime]:
    return parse_iso(value) if value else None


def upper_bound(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    moment = parse_iso(value)
    return moment.replace(hour=23, minute=59, second=59) if len(value) == 10 else moment


def check_period(start: Optional[datetime], end: Optional[datetime]) -> None:
    if start and end and start > end:
        raise ValidationError("Начало периода не может быть позже его конца")


def paginate(items: list, limit: Optional[int], offset: int) -> list:
    if (limit is not None and limit < 1) or offset < 0:
        raise ValidationError("limit должен быть больше 0, offset не может быть отрицательным")
    items = items[offset:]
    return items[:limit] if limit else items


def check_sort(sort_by: str, allowed: set) -> None:
    if sort_by not in allowed:
        raise ValidationError(f"Сортировка по полю {sort_by} не поддерживается")


def count_by(items: list, key: str) -> dict:
    result: dict = {}
    for item in items:
        result[item[key]] = result.get(item[key], 0) + 1
    return result
