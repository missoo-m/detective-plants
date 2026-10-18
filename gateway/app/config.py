import os

APP_TITLE = "Detective Plants — GraphQL Gateway"
HOST = os.getenv("GATEWAY_HOST", "0.0.0.0")
PORT = int(os.getenv("GATEWAY_PORT", "8000"))

AUTH_MODE = os.getenv("GATEWAY_AUTH_MODE", "mock")                              
AUTH_SERVICE_URL = os.getenv("GATEWAY_AUTH_SERVICE_URL", "http://localhost:8001")
AUTH_TIMEOUT_SECONDS = float(os.getenv("GATEWAY_AUTH_TIMEOUT", "3"))
MOCK_JWT_SECRET = os.getenv("GATEWAY_MOCK_JWT_SECRET", "mock-secret-change-me")   # только для режима mock
MOCK_SESSION_TTL = int(os.getenv("GATEWAY_MOCK_SESSION_TTL", "1800"))
