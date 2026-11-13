from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PhotoDTO:
    id: str
    url: str
    uploaded_at: str


@dataclass
class RequestDTO:
    id: str
    client_id: str
    expert_id: Optional[str]
    symptoms: str
    ai_prediagnosis: Optional[str]
    status: str
    created_at: str
    completed_at: Optional[str]
    photos: list[PhotoDTO] = field(default_factory=list)


@dataclass
class RequestDetailsDTO:
    request: RequestDTO
    photo_urls: list[str]
    ai_prediagnosis: Optional[str]


@dataclass
class DiseaseDTO:
    id: str
    name: str
    description: Optional[str]
    symptoms: Optional[str]
    treatment: Optional[str]


@dataclass
class RequestsSummaryDTO:
    total: int
    by_status: dict
