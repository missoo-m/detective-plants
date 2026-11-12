def build_handlers(service):
    def payment_completed(event, session):
        service.apply_payment(event["payload"]["request_id"])

    def tracker_completed(event, session):
        service.apply_tracker_completed(event["payload"]["request_id"])

    return {"PaymentCompleted": payment_completed, "TrackerCompleted": tracker_completed}
