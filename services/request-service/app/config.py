import os

SERVICE_NAME = "request-service"
DATABASE_URL = os.getenv(
    "REQUEST_DATABASE_URL",
    "postgresql://request:request_pass@localhost:5542/request_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"
