from app import clients
from app.context import build_context

EMAILS = {"user-1": "anna@example.com", "user-2": "ivan.expert@example.com", "user-3": "admin@example.com",
          "user-4": "petr@example.com", "user-5": "oleg@example.com"}


def token_for(user: str) -> str:
    return clients.security_client.login(EMAILS[user], "password123")["access_token"]


def ctx_for(user=None, token=None) -> dict:
    token = token or (token_for(user) if user else None)
    return build_context(f"Bearer {token}" if token else None)
