from .errors import BusinessRuleError


def build_handlers(service):
    def diagnosis_created(event, session):
        p = event["payload"]
        try:
            service.create_tracker(p["request_id"], p["client_id"], p["expert_id"], p.get("duration_days") or 14)
        except BusinessRuleError:
            pass

    return {"DiagnosisCreated": diagnosis_created}
