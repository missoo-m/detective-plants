import os

SERVICE_NAME = "notification-service"
DATABASE_URL = os.getenv(
    "NOTIFICATION_DATABASE_URL",
    "postgresql://notification:notification_pass@localhost:5437/notification_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"


GRPC_HOST = os.getenv("GRPC_HOST", "0.0.0.0")
GRPC_PORT = int(os.getenv("NOTIFICATION_GRPC_PORT", "50057"))
GRPC_TIMEOUT_SECONDS = float(os.getenv("GRPC_TIMEOUT_SECONDS", "3"))
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", os.getenv("AUTH_INTERNAL_API_KEY", "dev-internal-key"))
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", SERVICE_NAME)
OUTBOX_POLL_SECONDS = float(os.getenv("OUTBOX_POLL_SECONDS", "0.3"))
SEED_ON_START = os.getenv("SEED_ON_START", "1") == "1"
