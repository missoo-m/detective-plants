import copy
from typing import Optional
from ..errors import BusinessRuleError, NotFoundError, PermissionDeniedError, ValidationError
from .base import AdminClientBase
from .common import check_period, count_by, lower_bound, new_id, now_iso, parse_iso, upper_bound

MOCK_EXPERT_APPLICATIONS = {
    "app-1": {"id": "app-1", "user_id": "user-4", "documents_url": "https://minio/docs/user-4.pdf",
              "status": "PENDING", "submitted_at": "2026-01-18T10:00:00Z", "verified_at": None},
    "app-2": {"id": "app-2", "user_id": "user-2", "documents_url": "https://minio/docs/user-2.pdf",
              "status": "APPROVED", "submitted_at": "2026-01-03T09:00:00Z", "verified_at": "2026-01-05T12:00:00Z"},
}


class MockAdminClient(AdminClientBase):
    #Mock Admin Service

    def __init__(self):
        self.applications = copy.deepcopy(MOCK_EXPERT_APPLICATIONS)

    @staticmethod
    def _auth():
        from .. import clients
        return clients.auth_client

    def _require_admin(self, admin_id: str) -> None:
        user = self._auth().get_user(admin_id)
        if user["status"] != "ACTIVE" or user["role"] != "ADMIN":
            raise PermissionDeniedError("Действие доступно только администратору")

    def list_expert_applications(self, status=None, submitted_from=None, submitted_to=None,
                                 descending=True) -> list[dict]:
        start, end = lower_bound(submitted_from), upper_bound(submitted_to)
        check_period(start, end)
        items = list(self.applications.values())
        if status:
            items = [a for a in items if a["status"] == status]
        if start:
            items = [a for a in items if parse_iso(a["submitted_at"]) >= start]
        if end:
            items = [a for a in items if parse_iso(a["submitted_at"]) <= end]
        items.sort(key=lambda a: (a["submitted_at"], a["id"]), reverse=descending)
        return items

    def applications_summary(self) -> dict:
        items = list(self.applications.values())
        return {"total": len(items), "by_status": count_by(items, "status")}

    def submit_application(self, user_id: str, documents_url: str) -> dict:
        url = (documents_url or "").strip()
        if not url.startswith(("http://", "https://")) or len(url) > 500:
            raise ValidationError("documents_url должен быть ссылкой http(s) длиной до 500 символов")
        user = self._auth().get_user(user_id)
        if user["status"] != "ACTIVE":
            raise PermissionDeniedError("Учётная запись пользователя заблокирована или не активна")
        if user["role"] != "CLIENT":
            raise BusinessRuleError("Подать заявку может только пользователь с ролью CLIENT")
        app = next((a for a in self.applications.values() if a["user_id"] == user_id), None)
        if app is not None and app["status"] in ("PENDING", "APPROVED"):
            raise BusinessRuleError(f"Заявка уже существует (статус {app['status']})")
        if app is None:
            app = {"id": new_id("app"), "user_id": user_id}
            self.applications[app["id"]] = app
        app.update(documents_url=url, status="PENDING", submitted_at=now_iso(), verified_at=None)
        return app

    def verify_expert(self, application_id: str, admin_id: str, approve: bool) -> dict:
        self._require_admin(admin_id)
        app = self.applications.get(application_id)
        if app is None:
            raise NotFoundError(f"Заявка эксперта {application_id} не найдена")
        if app["status"] != "PENDING":
            raise BusinessRuleError(f"Заявка уже рассмотрена (статус {app['status']})")
        app["status"], app["verified_at"] = ("APPROVED" if approve else "REJECTED"), now_iso()
        if approve:
            self._auth().assign_role(app["user_id"], "EXPERT")
        return app

    def block_user(self, admin_id: str, user_id: str) -> dict:
        self._require_admin(admin_id)
        target = self._auth().get_user(user_id)
        if target["role"] == "ADMIN":
            raise BusinessRuleError("Администратора заблокировать нельзя")
        if target["status"] == "BLOCKED":
            raise BusinessRuleError("Пользователь уже заблокирован")
        self._auth().set_status(user_id, "BLOCKED")
        return {"user_id": user_id, "status": "BLOCKED"}
