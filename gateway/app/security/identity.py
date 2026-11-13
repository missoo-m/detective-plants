from dataclasses import dataclass

CLIENT, EXPERT, ADMIN = "CLIENT", "EXPERT", "ADMIN"


@dataclass(frozen=True)
class Identity:
    user_id: str
    role: str
    session_id: str

    @property
    def is_admin(self) -> bool:
        return self.role == ADMIN
