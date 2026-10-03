from dataclasses import dataclass


@dataclass
class ExpertStatsDTO:
    expert_id: str
    total_requests: int
    completed_requests: int
    avg_rating: float


@dataclass
class DiseaseStatsDTO:
    disease_id: str
    count: int
    period: str
