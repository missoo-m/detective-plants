import os

SERVICE_NAME = "satellite-service"
DATABASE_URL = os.getenv(
    "SATELLITE_DATABASE_URL",
    "postgresql://satellite:satellite_pass@localhost:5440/satellite_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"
