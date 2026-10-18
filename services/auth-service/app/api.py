from typing import Optional

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import config
from .errors import (AuthenticationError, BusinessRuleError, InvalidValueError, NotFoundError,
                     PermissionDeniedError, ServiceError)
from .session_manager import SessionManager
from .sessions import InMemorySessionStore, RedisSessionStore, SessionStore

STATUS_CODES = {AuthenticationError: 401, PermissionDeniedError: 403, NotFoundError: 404,
                BusinessRuleError: 409, InvalidValueError: 422}
ERROR_CODES = {AuthenticationError: "UNAUTHENTICATED", PermissionDeniedError: "FORBIDDEN", NotFoundError: "NOT_FOUND",
               BusinessRuleError: "BUSINESS_RULE_VIOLATION", InvalidValueError: "BAD_USER_INPUT"}


class RegisterBody(BaseModel):
    email: str
    password: str
    name: str


class LoginBody(BaseModel):
    email: str
    password: str


class ValueBody(BaseModel):
    value: str


def build_store() -> SessionStore:
    if config.SESSION_STORE == "memory":
        return InMemorySessionStore()
    import redis
    return RedisSessionStore(redis.Redis.from_url(config.REDIS_URL, decode_responses=True))


def build_manager() -> SessionManager:
    from .service import AuthService
    return SessionManager(AuthService(), build_store(), config.JWT_SECRET, config.JWT_ISSUER,
                          config.JWT_TTL_SECONDS, config.SESSION_TTL_SECONDS, config.SESSION_SLIDING)


def _bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer ") or not authorization[7:].strip():
        raise AuthenticationError("Требуется заголовок Authorization: Bearer <token>")
    return authorization[7:].strip()


def create_app(manager: Optional[SessionManager] = None) -> FastAPI:
    app = FastAPI(title="Auth Service")
    holder = {"manager": manager}

    def mgr() -> SessionManager:                    
        if holder["manager"] is None:
            holder["manager"] = build_manager()
        return holder["manager"]

    @app.exception_handler(ServiceError)
    async def on_service_error(_, exc: ServiceError):
        kind = next((k for k in STATUS_CODES if isinstance(exc, k)), None)
        return JSONResponse(status_code=STATUS_CODES.get(kind, 500),
                            content={"detail": str(exc), "code": ERROR_CODES.get(kind, "INTERNAL_ERROR")})

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "auth-service"}

    @app.post("/auth/register", status_code=201)
    def register(body: RegisterBody):
        return mgr().register(body.email, body.password, body.name)

    @app.post("/auth/login")
    def login(body: LoginBody):
        return mgr().login(body.email, body.password)

    @app.post("/auth/verify")
    def verify(authorization: Optional[str] = Header(default=None)):
        return mgr().verify(_bearer(authorization))

    @app.post("/auth/logout")
    def logout(authorization: Optional[str] = Header(default=None)):
        return {"revoked": mgr().logout(_bearer(authorization))}

    @app.post("/auth/logout-all")
    def logout_all(authorization: Optional[str] = Header(default=None)):
        return {"revoked": mgr().logout_all(_bearer(authorization))}

    def _internal(key: Optional[str]) -> None:
        if key != config.INTERNAL_API_KEY:
            raise PermissionDeniedError("Недопустимый ключ внутреннего API")

    @app.put("/internal/users/{user_id}/status")
    def set_status(user_id: str, body: ValueBody, x_internal_key: Optional[str] = Header(default=None)):
        _internal(x_internal_key)
        user = mgr()._directory.set_status(user_id, body.value)
        revoked = mgr().revoke_user_sessions(user_id) if body.value != "ACTIVE" else 0
        return {"user_id": user.id, "status": user.status, "revoked_sessions": revoked}

    @app.put("/internal/users/{user_id}/role")
    def set_role(user_id: str, body: ValueBody, x_internal_key: Optional[str] = Header(default=None)):
        _internal(x_internal_key)
        user = mgr()._directory.assign_role(user_id, body.value)
        return {"user_id": user.id, "role": user.role}          

    return app


app = create_app()
