import os

SERVICE_NAME = "admin-service"
DATABASE_URL = os.getenv(
    "ADMIN_DATABASE_URL",
    "postgresql://admin:admin_pass@localhost:5439/admin_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"
