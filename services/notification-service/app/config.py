import os

SERVICE_NAME = "notification-service"
DATABASE_URL = os.getenv(
    "NOTIFICATION_DATABASE_URL",
    "postgresql://notification:notification_pass@localhost:5437/notification_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"
