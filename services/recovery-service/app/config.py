import os

SERVICE_NAME = "recovery-service"
DATABASE_URL = os.getenv(
    "RECOVERY_DATABASE_URL",
    "postgresql://recovery:recovery_pass@localhost:5434/recovery_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"
