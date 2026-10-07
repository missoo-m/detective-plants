import os

SERVICE_NAME = "auth-service"
DATABASE_URL = os.getenv(
    "AUTH_DATABASE_URL",
    "postgresql://auth:auth_pass@localhost:5431/auth_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-secret-change-me")
TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "3600"))
