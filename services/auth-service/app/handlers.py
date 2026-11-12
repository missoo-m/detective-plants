def build_handlers(service):
    sessions = service.session_manager

    def expert_verified(event, session):
        service.assign_role(event["payload"]["user_id"], "EXPERT")

    def user_blocked(event, session):
        user_id = event["payload"]["user_id"]
        service.set_status(user_id, "BLOCKED")
        sessions.revoke_user_sessions(user_id)            

    return {"ExpertVerified": expert_verified, "UserBlocked": user_blocked}
