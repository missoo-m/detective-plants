import os

SERVICE_NAME = "auth-service"
DATABASE_URL = os.getenv(
    "AUTH_DATABASE_URL",
    "postgresql://auth:auth_pass@localhost:5431/auth_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"
JWT_SECRET = os.getenv("AUTH_JWT_SECRET", "dev-secret-change-me")
JWT_ISSUER = os.getenv("AUTH_JWT_ISSUER", "plant-detective-auth")
JWT_TTL_SECONDS = int(os.getenv("AUTH_JWT_TTL_SECONDS", "3600"))            # срок жизни самого токена
SESSION_TTL_SECONDS = int(os.getenv("AUTH_SESSION_TTL_SECONDS", "1800"))    # TTL сессии в Redis
SESSION_SLIDING = os.getenv("AUTH_SESSION_SLIDING", "1") == "1"            # продлевать сессию при активности
SESSION_STORE = os.getenv("AUTH_SESSION_STORE", "redis")                    # redis 
REDIS_URL = os.getenv("AUTH_REDIS_URL", "redis://localhost:6379/0")
INTERNAL_API_KEY = os.getenv("AUTH_INTERNAL_API_KEY", "dev-internal-key")  
GRPC_HOST = os.getenv("GRPC_HOST", "0.0.0.0")
GRPC_PORT = int(os.getenv("AUTH_GRPC_PORT", "50051"))
GRPC_TIMEOUT_SECONDS = float(os.getenv("GRPC_TIMEOUT_SECONDS", "3"))
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", os.getenv("AUTH_INTERNAL_API_KEY", "dev-internal-key"))
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", SERVICE_NAME)
OUTBOX_POLL_SECONDS = float(os.getenv("OUTBOX_POLL_SECONDS", "0.3"))
SEED_ON_START = os.getenv("SEED_ON_START", "1") == "1"         
