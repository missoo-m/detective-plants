import os

SERVICE_NAME = "payment-service"
DATABASE_URL = os.getenv(
    "PAYMENT_DATABASE_URL",
    "postgresql://payment:payment_pass@localhost:5436/payment_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"
