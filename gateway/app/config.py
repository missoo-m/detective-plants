import os

APP_TITLE = "Detective Plants — GraphQL Gateway"
HOST = os.getenv("GATEWAY_HOST", "0.0.0.0")
PORT = int(os.getenv("GATEWAY_PORT", "8000"))

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key")      
GRPC_TIMEOUT_SECONDS = float(os.getenv("GATEWAY_GRPC_TIMEOUT", "5"))

SERVICE_ADDRESSES = {
    "auth": os.getenv("AUTH_GRPC_ADDR", "localhost:50051"),
    "request": os.getenv("REQUEST_GRPC_ADDR", "localhost:50052"),
    "expert": os.getenv("EXPERT_GRPC_ADDR", "localhost:50053"),
    "recovery": os.getenv("RECOVERY_GRPC_ADDR", "localhost:50054"),
    "chat": os.getenv("CHAT_GRPC_ADDR", "localhost:50055"),
    "payment": os.getenv("PAYMENT_GRPC_ADDR", "localhost:50056"),
    "notification": os.getenv("NOTIFICATION_GRPC_ADDR", "localhost:50057"),
    "analytics": os.getenv("ANALYTICS_GRPC_ADDR", "localhost:50058"),
    "admin": os.getenv("ADMIN_GRPC_ADDR", "localhost:50059"),
    "satellite": os.getenv("SATELLITE_GRPC_ADDR", "localhost:50060"),
}
