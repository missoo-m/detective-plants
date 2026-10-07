import os

SERVICE_NAME = "request-service"
DATABASE_URL = os.getenv(
    "REQUEST_DATABASE_URL",
    "postgresql://request:request_pass@localhost:5432/request_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"

MAX_ACTIVE_REQUESTS = int(os.getenv("REQUEST_MAX_ACTIVE", "3"))
MAX_PHOTOS = 5
MAX_FILE_BYTES = 5 * 1024 * 1024
