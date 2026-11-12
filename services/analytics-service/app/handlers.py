from .repository import StatsRepository
from .utils import parse_uuid


def _period(event: dict) -> str:
    return event["timestamp"][:7]                        


def build_handlers(service=None):
    def counting(extra=None):
        def handler(event, session):
            repo = StatsRepository(session)
            amount = float(event["payload"].get("amount") or 0) if event["event_type"] == "PaymentCompleted" else 0.0
            repo.bump_counter(event["event_type"], _period(event), amount)
            if extra:
                extra(repo, event)
        return handler

    def expert_selected(repo, event):
        repo.bump_expert(parse_uuid(event["payload"]["expert_id"]), total=1)

    def tracker_completed(repo, event):
        repo.bump_expert(parse_uuid(event["payload"]["expert_id"]), completed=1)

    def diagnosis_created(repo, event):
        repo.bump_disease(parse_uuid(event["payload"]["disease_id"]), _period(event))

    return {"UserRegistered": counting(), "RequestCreated": counting(), "ExpertResponseCreated": counting(),
            "ExpertSelected": counting(expert_selected), "PaymentCompleted": counting(),
            "DiagnosisCreated": counting(diagnosis_created), "TrackerCreated": counting(),
            "TrackerCompleted": counting(tracker_completed), "SatelliteAlertCreated": counting()}
