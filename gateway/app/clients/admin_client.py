from typing import Optional
from .base import AdminClientBase

MOCK_EXPERT_APPLICATIONS = [
    {"id": "app-1", "user_id": "user-4", "documents_url": "https://minio/docs/user-4.pdf",
     "status": "PENDING", "submitted_at": "2026-01-18T10:00:00Z", "verified_at": None},
    {"id": "app-2", "user_id": "user-2", "documents_url": "https://minio/docs/user-2.pdf",
     "status": "APPROVED", "submitted_at": "2026-01-03T09:00:00Z",
     "verified_at": "2026-01-05T12:00:00Z"},
]

#Mock-клиент Admin Service
class MockAdminClient(AdminClientBase):
    def list_expert_applications(self, status: Optional[str] = None) -> list[dict]:
        apps = list(MOCK_EXPERT_APPLICATIONS)
        if status:
            apps = [a for a in apps if a["status"] == status]
        return apps
