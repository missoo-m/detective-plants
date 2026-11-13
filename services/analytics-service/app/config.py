import os

SERVICE_NAME = "analytics-service"
DATABASE_URL = os.getenv(
    "ANALYTICS_DATABASE_URL",
    "postgresql://analytics:analytics_pass@localhost:5438/analytics_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"


GRPC_HOST = os.getenv("GRPC_HOST", "0.0.0.0")
GRPC_PORT = int(os.getenv("ANALYTICS_GRPC_PORT", "50058"))
GRPC_TIMEOUT_SECONDS = float(os.getenv("GRPC_TIMEOUT_SECONDS", "3"))
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", os.getenv("AUTH_INTERNAL_API_KEY", "dev-internal-key"))
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", SERVICE_NAME)
OUTBOX_POLL_SECONDS = float(os.getenv("OUTBOX_POLL_SECONDS", "0.3"))
SEED_ON_START = os.getenv("SEED_ON_START", "1") == "1"


GRPC_RETRIES = int(os.getenv("GRPC_RETRIES", "2"))
GRPC_BACKOFF_BASE = float(os.getenv("GRPC_BACKOFF_BASE", "0.2"))
GRPC_BACKOFF_MAX = float(os.getenv("GRPC_BACKOFF_MAX", "2"))
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "1") == "1"
REDIS_CACHE_URL = os.getenv("REDIS_CACHE_URL", "redis://localhost:6379/1")
REDIS_TIMEOUT_SECONDS = float(os.getenv("REDIS_TIMEOUT_SECONDS", "0.3"))
