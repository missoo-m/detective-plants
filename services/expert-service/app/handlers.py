def build_handlers(service):
    def expert_selected(event, session):
        payload = event["payload"]
        service.accept_response(payload["request_id"], payload["expert_id"])

    return {"ExpertSelected": expert_selected}
