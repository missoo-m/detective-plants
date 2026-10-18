from strawberry.permission import BasePermission

from ..errors import AuthenticationError, PermissionDeniedError
from .policy import AUTHENTICATED, POLICY, PUBLIC


def access(operation: str) -> type:
    rule = POLICY[operation]

    class OperationPermission(BasePermission):
        message = f"Доступ к операции {operation} запрещён"

        def has_permission(self, source, info, **kwargs) -> bool:
            if rule == PUBLIC:
                return True
            identity = info.context.get("identity")
            if identity is None:
                raise AuthenticationError(info.context.get("auth_error") or
                                          "Требуется аутентификация: передайте заголовок Authorization: Bearer <JWT>")
            if rule == AUTHENTICATED or identity.role in rule:
                return True
            raise PermissionDeniedError(f"Операция {operation} недоступна для роли {identity.role}")

    OperationPermission.__name__ = f"Access[{operation}]"
    return OperationPermission
