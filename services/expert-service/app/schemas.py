from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ResponseDTO:
    id: str
    request_id: str
    expert_id: str
    comment: Optional[str]
    status: str
    created_at: str


@dataclass
class TreatmentStepDTO:
    id: str
    step: str
    frequency: Optional[str]
    duration_days: Optional[int]


@dataclass
class DiagnosisDTO:
    id: str
    request_id: str
    expert_id: str
    disease_id: str
    description: Optional[str]
    ai_prediagnosis: Optional[str]
    duration_days: int
    created_at: str
    checklist: list[TreatmentStepDTO] = field(default_factory=list)


@dataclass
class ResponsesSummaryDTO:
    total: int
    by_status: dict
