import os

SERVICE_NAME = "analytics-service"
DATABASE_URL = os.getenv(
    "ANALYTICS_DATABASE_URL",
    "postgresql://analytics:analytics_pass@localhost:5438/analytics_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"
