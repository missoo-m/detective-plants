import os

SERVICE_NAME = "payment-service"
DATABASE_URL = os.getenv(
    "PAYMENT_DATABASE_URL",
    "postgresql://payment:payment_pass@localhost:5436/payment_db",
)
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"

from decimal import Decimal

SERVICE_PRICE = Decimal(os.getenv("PAYMENT_SERVICE_PRICE", "25.00"))       
COMMISSION_RATE = Decimal(os.getenv("PAYMENT_COMMISSION_RATE", "0.10"))    
MIN_WITHDRAWAL = Decimal(os.getenv("PAYMENT_MIN_WITHDRAWAL", "10.00"))
