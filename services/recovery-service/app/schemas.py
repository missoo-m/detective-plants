from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HistoryDTO:
    id: str
    record_type: str
    date: str
    photo_url: Optional[str]
    change_description: Optional[str]
    author_id: str


@dataclass
class TrackerDTO:
    id: str
    request_id: str
    client_id: str
    expert_id: str
    start_date: str
    end_date: Optional[str]
    status: str
    current_stage: Optional[str]
    history: list[HistoryDTO] = field(default_factory=list)


@dataclass
class ProgressDTO:
    tracker_id: str
    total_days: int
    elapsed_days: int
    percent: float
    photos_count: int
    updates_count: int
