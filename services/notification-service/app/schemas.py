from dataclasses import dataclass


@dataclass
class NotificationDTO:
    id: str
    user_id: str
    type: str
    message: str
    status: str
    created_at: str
