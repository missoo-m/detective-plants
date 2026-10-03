import os

SERVICE_NAME = "chat-service"
DATABASE_URL = os.getenv(
    "CHAT_DATABASE_URL",
    "postgresql://chat:chat_pass@localhost:5435/chat_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"
