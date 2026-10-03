from dataclasses import dataclass
from typing import Optional


@dataclass
class ProfileDTO:
    id: str
    photo_url: Optional[str]
    description: Optional[str]
    rating: float
    language: str


@dataclass
class UserDTO:
    id: str
    email: str
    name: str
    role: Optional[str]
    status: str
    created_at: str
    profile: Optional[ProfileDTO]


@dataclass
class ValidationResult:
    valid: bool
    role: Optional[str] = None
    status: Optional[str] = None
