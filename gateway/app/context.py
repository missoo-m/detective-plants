from typing import Optional

from fastapi import Header

from . import clients
from .errors import AuthenticationError


def build_context(authorization: Optional[str]) -> dict:
    context = {"identity": None, "current_user_id": None, "token": None, "auth_error": None}
    if not authorization:
        return context
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        context["auth_error"] = "Заголовок Authorization должен иметь вид: Bearer <token>"
        return context
    context["token"] = token.strip()
    try:
        identity = clients.security_client.verify(context["token"])
    except AuthenticationError as error:
        context["auth_error"] = error.message          
        return context
    context["identity"], context["current_user_id"] = identity, identity.user_id
    return context


def get_context(authorization: Optional[str] = Header(default=None)) -> dict:
    return build_context(authorization)
