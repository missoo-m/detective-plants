from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .utils import fmt_dt as _fmt, parse_uuid as _parse_uuid
from .errors import InvalidValueError, NotFoundError
from .models import User
from .repository import UserRepository
from .schemas import ProfileDTO, UserDTO, ValidationResult

ROLES = {"CLIENT", "EXPERT", "ADMIN"}
USER_STATUSES = {"ACTIVE", "BLOCKED", "PENDING"}


def _to_dto(user: User) -> UserDTO:
    profile = None
    if user.profile:
        p = user.profile
        profile = ProfileDTO(
            id=str(p.id),
            photo_url=p.photo_url,
            description=p.description,
            rating=p.rating or 0.0,
            language=p.language or "ru",
        )
    return UserDTO(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role.name if user.role else None,
        status=user.status,
        created_at=_fmt(user.created_at),
        profile=profile,
    )


class AuthService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    def get_user(self, user_id: str) -> UserDTO:
        uid = _parse_uuid(user_id)
        with self._session_factory() as session:
            user = UserRepository(session).get_by_id(uid)
            if user is None:
                raise NotFoundError(f"Пользователь {user_id} не найден")
            return _to_dto(user)

    def list_users(self, role: Optional[str] = None, status: Optional[str] = None) -> list[UserDTO]:
        if role is not None and role not in ROLES:
            raise InvalidValueError(f"Неизвестная роль: {role}")
        if status is not None and status not in USER_STATUSES:
            raise InvalidValueError(f"Неизвестный статус: {status}")
        with self._session_factory() as session:
            users = UserRepository(session).list_users(role, status)
            return [_to_dto(u) for u in users]

    def validate_user(self, user_id: str) -> ValidationResult:
        try:
            uid = _parse_uuid(user_id)
        except InvalidValueError:
            return ValidationResult(valid=False)
        with self._session_factory() as session:
            user = UserRepository(session).get_by_id(uid)
            if user is None:
                return ValidationResult(valid=False)
            return ValidationResult(
                valid=user.status == "ACTIVE",
                role=user.role.name if user.role else None,
                status=user.status,
            )
