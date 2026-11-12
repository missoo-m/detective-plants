import os

SERVICE_NAME = "recovery-service"
DATABASE_URL = os.getenv(
    "RECOVERY_DATABASE_URL",
    "postgresql://recovery:recovery_pass@localhost:5434/recovery_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"


GRPC_HOST = os.getenv("GRPC_HOST", "0.0.0.0")
GRPC_PORT = int(os.getenv("RECOVERY_GRPC_PORT", "50054"))
GRPC_TIMEOUT_SECONDS = float(os.getenv("GRPC_TIMEOUT_SECONDS", "3"))
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", os.getenv("AUTH_INTERNAL_API_KEY", "dev-internal-key"))
NOTIFICATION_GRPC_ADDR = os.getenv("NOTIFICATION_GRPC_ADDR", "localhost:50057")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", SERVICE_NAME)
OUTBOX_POLL_SECONDS = float(os.getenv("OUTBOX_POLL_SECONDS", "0.3"))
SEED_ON_START = os.getenv("SEED_ON_START", "1") == "1"

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "0") == "1"
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "plant-photos")
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")
