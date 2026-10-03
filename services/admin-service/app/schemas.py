from dataclasses import dataclass
from typing import Optional


@dataclass
class ApplicationDTO:
    id: str
    user_id: str
    documents_url: Optional[str]
    status: str
    submitted_at: str
    verified_at: Optional[str]
