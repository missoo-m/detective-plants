from dataclasses import dataclass
from typing import Optional


@dataclass
class ChatRoomDTO:
    id: str
    request_id: str
    client_id: str
    expert_id: str
    status: str
    created_at: str


@dataclass
class MessageDTO:
    id: str
    chat_room_id: str
    sender_id: str
    text: Optional[str]
    attachment_url: Optional[str]
    is_read: bool
    sent_at: str


@dataclass
class VideoRoomDTO:
    id: str
    chat_room_id: str
    room_url: str
    status: str
    recording_url: Optional[str]
    created_at: str
    finished_at: Optional[str]


@dataclass
class ModerationRuleDTO:
    id: str
    name: str
    pattern: str
    action: str


@dataclass
class ModerationResultDTO:
    allowed: bool
    action: Optional[str] = None
    rule_name: Optional[str] = None
