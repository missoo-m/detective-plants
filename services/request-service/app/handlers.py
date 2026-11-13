def build_handlers(service):
    def payment_completed(event, session):
        p = event["payload"]
        service.apply_payment(p["request_id"], p.get("transaction_id"), p.get("client_id"))

    def tracker_completed(event, session):
        service.apply_tracker_completed(event["payload"]["request_id"])

    return {"PaymentCompleted": payment_completed, "TrackerCompleted": tracker_completed}
