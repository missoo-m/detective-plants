import re
import uuid
from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from .models import Profile, ReferralProfile, User, UserSettings
from .repository import SORT_COLUMNS, UserRepository
from .schemas import AuthResultDTO, ProfileDTO, UserDTO, UsersSummaryDTO, ValidationResult
from .security import hash_password, issue_token, verify_password
from .utils import fmt_dt, parse_uuid

ROLES = {"CLIENT", "EXPERT", "ADMIN"}
USER_STATUSES = {"ACTIVE", "BLOCKED", "PENDING"}
LANGUAGES = {"ru", "en", "be"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def _to_dto(user: User) -> UserDTO:
    profile = None
    if user.profile:
        p = user.profile
        profile = ProfileDTO(id=str(p.id), photo_url=p.photo_url, description=p.description,
                             rating=p.rating or 0.0, language=p.language or "ru")
    return UserDTO(id=str(user.id), email=user.email, name=user.name,
                   role=user.role.name if user.role else None, status=user.status,
                   created_at=fmt_dt(user.created_at), profile=profile)


class AuthService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    def get_user(self, user_id: str) -> UserDTO:
        uid = parse_uuid(user_id)
        with self._session_factory() as session:
            user = UserRepository(session).get_by_id(uid)
            if user is None:
                raise NotFoundError(f"Пользователь {user_id} не найден")
            return _to_dto(user)

    def list_users(self, role: Optional[str] = None, status: Optional[str] = None,
                   search: Optional[str] = None, sort_by: str = "created_at", descending: bool = False,
                   limit: Optional[int] = None, offset: int = 0) -> list[UserDTO]:
        if role is not None and role not in ROLES:
            raise InvalidValueError(f"Неизвестная роль: {role}")
        if status is not None and status not in USER_STATUSES:
            raise InvalidValueError(f"Неизвестный статус: {status}")
        if sort_by not in SORT_COLUMNS:
            raise InvalidValueError(f"Сортировка по полю {sort_by} не поддерживается")
        if (limit is not None and limit < 1) or offset < 0:
            raise InvalidValueError("limit должен быть больше 0, offset не может быть отрицательным")
        with self._session_factory() as session:
            users = UserRepository(session).list_users(role, status, search, sort_by, descending, limit, offset)
            return [_to_dto(u) for u in users]

    def users_summary(self) -> UsersSummaryDTO:
        with self._session_factory() as session:
            repo = UserRepository(session)
            by_role, by_status = repo.count_by_role(), repo.count_by_status()
            return UsersSummaryDTO(total=sum(by_status.values()), by_role=by_role, by_status=by_status)

    def validate_user(self, user_id: str) -> ValidationResult:
        try:
            uid = parse_uuid(user_id)
        except InvalidValueError:
            return ValidationResult(valid=False)
        with self._session_factory() as session:
            user = UserRepository(session).get_by_id(uid)
            if user is None:
                return ValidationResult(valid=False)
            return ValidationResult(valid=user.status == "ACTIVE",
                                    role=user.role.name if user.role else None, status=user.status)

    def register(self, email: str, password: str, name: str) -> UserDTO:
        email = (email or "").strip().lower()
        name = (name or "").strip()
        if not EMAIL_RE.match(email):
            raise InvalidValueError("Некорректный email")
        if len(password or "") < MIN_PASSWORD_LENGTH:
            raise InvalidValueError(f"Пароль должен содержать не менее {MIN_PASSWORD_LENGTH} символов")
        if not 2 <= len(name) <= 100:
            raise InvalidValueError("Имя должно содержать от 2 до 100 символов")
        with self._session_factory() as session:
            repo = UserRepository(session)
            if repo.get_by_email(email):
                raise BusinessRuleError("Пользователь с таким email уже зарегистрирован")
            role = repo.get_role("CLIENT")
            if role is None:
                raise BusinessRuleError("Роль CLIENT не настроена (выполните seed)")
            user = User(email=email, name=name, password_hash=hash_password(password),
                        status="ACTIVE", role=role)
            user.profile = Profile(language="ru", rating=0)
            user.settings = UserSettings()
            user.referral_profile = ReferralProfile(
                referral_link=f"https://detective-plants.example/ref/{uuid.uuid4().hex[:10]}")
            repo.add(user)
            session.commit()
            return _to_dto(user)

    def login(self, email: str, password: str) -> AuthResultDTO:
        with self._session_factory() as session:
            user = UserRepository(session).get_by_email((email or "").strip().lower())
            if user is None or not verify_password(password or "", user.password_hash):
                raise PermissionDeniedError("Неверный email или пароль")
            if user.status != "ACTIVE":
                raise PermissionDeniedError("Учётная запись заблокирована или не активирована")
            return AuthResultDTO(token=issue_token(str(user.id)), user=_to_dto(user))

    def update_profile(self, user_id: str, name: Optional[str] = None, photo_url: Optional[str] = None,
                       description: Optional[str] = None, language: Optional[str] = None) -> UserDTO:
        uid = parse_uuid(user_id)
        if name is not None and not 2 <= len(name.strip()) <= 100:
            raise InvalidValueError("Имя должно содержать от 2 до 100 символов")
        if language is not None and language not in LANGUAGES:
            raise InvalidValueError(f"Язык {language} не поддерживается")
        if photo_url is not None and not photo_url.startswith(("http://", "https://")):
            raise InvalidValueError("photo_url должен быть ссылкой http(s)")
        with self._session_factory() as session:
            user = UserRepository(session).get_by_id(uid)
            if user is None:
                raise NotFoundError(f"Пользователь {user_id} не найден")
            if user.status != "ACTIVE":
                raise PermissionDeniedError("Профиль заблокированного пользователя изменять нельзя")
            if user.profile is None:
                user.profile = Profile(language="ru", rating=0)
            if name is not None:
                user.name = name.strip()
            if photo_url is not None:
                user.profile.photo_url = photo_url
            if description is not None:
                user.profile.description = description
            if language is not None:
                user.profile.language = language
            session.commit()
            return _to_dto(user)

    def assign_role(self, user_id: str, role: str) -> UserDTO:
        if role not in ROLES:
            raise InvalidValueError(f"Неизвестная роль: {role}")
        uid = parse_uuid(user_id)
        with self._session_factory() as session:
            repo = UserRepository(session)
            user = repo.get_by_id(uid)
            if user is None:
                raise NotFoundError(f"Пользователь {user_id} не найден")
            if user.role and user.role.name == "ADMIN":
                raise BusinessRuleError("Роль администратора изменять нельзя")
            new_role = repo.get_role(role)
            if new_role is None:
                raise BusinessRuleError(f"Роль {role} не настроена")
            user.role = new_role
            session.commit()
            return _to_dto(user)

    def set_status(self, user_id: str, status: str) -> UserDTO:
        if status not in USER_STATUSES:
            raise InvalidValueError(f"Неизвестный статус: {status}")
        uid = parse_uuid(user_id)
        with self._session_factory() as session:
            user = UserRepository(session).get_by_id(uid)
            if user is None:
                raise NotFoundError(f"Пользователь {user_id} не найден")
            if user.role and user.role.name == "ADMIN" and status != "ACTIVE":
                raise BusinessRuleError("Администратора нельзя заблокировать")
            user.status = status
            session.commit()
            return _to_dto(user)
