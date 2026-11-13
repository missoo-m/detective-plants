from dataclasses import dataclass


@dataclass
class NotificationDTO:
    id: str
    user_id: str
    type: str
    message: str
    status: str
    created_at: str


@dataclass
class NotificationsSummaryDTO:
    total: int
    unread: int
    by_type: dict
