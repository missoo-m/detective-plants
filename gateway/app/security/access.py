from typing import Optional

from ..errors import PermissionDeniedError
from .identity import ADMIN, CLIENT, EXPERT, Identity


def identity_of(info) -> Identity:
    return info.context["identity"]


def deny(message: str = "Недостаточно прав для доступа к этим данным"):
    raise PermissionDeniedError(message)


def assert_self_or_admin(identity: Identity, user_id: str) -> None:
    if not identity.is_admin and identity.user_id != user_id:
        deny("Можно просматривать только свои данные")


def assert_case_access(identity: Identity, request: dict) -> None:
    """Диагноз, трекер, заявка: автор, назначенный эксперт или администратор."""
    if not (identity.is_admin or identity.user_id in (request.get("client_id"), request.get("expert_id"))):
        deny("Заявка принадлежит другому пользователю")


def assert_request_access(identity: Identity, request: dict) -> None:
    """Заявку видят участники и администратор; эксперты — ещё и новые заявки из общей очереди."""
    if identity.role == EXPERT and request.get("status") == "CREATED":
        return
    assert_case_access(identity, request)


def assert_owner_or_admin(identity: Identity, owner_id: str) -> None:
    if not (identity.is_admin or identity.user_id == owner_id):
        deny("Данные принадлежат другому пользователю")


def expert_scope(identity: Identity, expert_id: Optional[str]) -> Optional[str]:
    """Эксперт видит только свои данные; администратор — любые."""
    if identity.role == EXPERT:
        if expert_id not in (None, identity.user_id):
            deny("Эксперт может запрашивать только свои данные")
        return identity.user_id
    return expert_id


def scoped_filters(identity: Identity, client_id: Optional[str] = None, expert_id: Optional[str] = None) -> dict:
    """Область данных по роли: клиент — только как клиент, эксперт — только как эксперт, админ — как запросил."""
    if identity.role == CLIENT:
        if client_id not in (None, identity.user_id):
            deny("Клиент может запрашивать только свои данные")
        return {"client_id": identity.user_id, "expert_id": None}
    if identity.role == EXPERT:
        if expert_id not in (None, identity.user_id):
            deny("Эксперт может запрашивать только свои данные")
        return {"client_id": None, "expert_id": identity.user_id}
    return {"client_id": client_id, "expert_id": expert_id}
