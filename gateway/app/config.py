import os

APP_TITLE = "Detective Plants — GraphQL Gateway"
HOST = os.getenv("GATEWAY_HOST", "0.0.0.0")
PORT = int(os.getenv("GATEWAY_PORT", "8000"))

# Пока нет JWT "текущий пользователь" берётся из заголовка.
DEFAULT_USER_ID = os.getenv("GATEWAY_DEFAULT_USER_ID", "user-1")
