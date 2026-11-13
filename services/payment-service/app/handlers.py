def build_handlers(service):
    def payment_rejected(event, session):
        p = event["payload"]
        service.refund_payment(p["transaction_id"], p.get("reason", ""))

    return {"PaymentRejected": payment_rejected}
