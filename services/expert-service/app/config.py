import os

SERVICE_NAME = "expert-service"
DATABASE_URL = os.getenv(
    "EXPERT_DATABASE_URL",
    "postgresql://expert:expert_pass@localhost:5433/expert_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"
