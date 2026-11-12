def build_handlers(service):
    def payment_completed(event, session):
        p = event["payload"]
        service.open_room(p["request_id"], p["client_id"], p["expert_id"])

    return {"PaymentCompleted": payment_completed}
