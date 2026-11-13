from .identity import ADMIN, CLIENT, EXPERT

PUBLIC = "PUBLIC"
AUTHENTICATED = "AUTHENTICATED"

POLICY: dict = {
    "Query.me": AUTHENTICATED,
    "Query.user": AUTHENTICATED,
    "Query.users": frozenset({ADMIN}),
    "Query.usersSummary": frozenset({ADMIN}),
    "Query.request": AUTHENTICATED,
    "Query.myRequests": frozenset({CLIENT}),
    "Query.availableRequests": frozenset({EXPERT, ADMIN}),
    "Query.requestsByExpert": frozenset({EXPERT, ADMIN}),
    "Query.requestsSummary": AUTHENTICATED,
    "Query.diagnosis": AUTHENTICATED,
    "Query.diagnosisByRequest": AUTHENTICATED,
    "Query.responsesSummary": frozenset({EXPERT, ADMIN}),
    "Query.tracker": AUTHENTICATED,
    "Query.trackerByRequest": AUTHENTICATED,
    "Query.trackerProgress": AUTHENTICATED,
    "Query.chatRoom": AUTHENTICATED,
    "Query.chatRoomByRequest": AUTHENTICATED,
    "Query.chatUnreadCount": AUTHENTICATED,
    "Query.notifications": AUTHENTICATED,
    "Query.notificationsSummary": AUTHENTICATED,
    "Query.transactions": AUTHENTICATED,
    "Query.transactionsSummary": AUTHENTICATED,
    "Query.withdrawals": frozenset({EXPERT, ADMIN}),
    "Query.expertBalance": frozenset({EXPERT, ADMIN}),
    "Query.expertApplications": frozenset({ADMIN}),
    "Query.applicationsSummary": frozenset({ADMIN}),
    "Query.expertStats": frozenset({EXPERT, ADMIN}),
    "Query.topExperts": AUTHENTICATED,
    "Query.diseaseStats": AUTHENTICATED,
    "Query.platformSummary": frozenset({ADMIN}),
    "Query.myFields": frozenset({CLIENT}),
    "Query.satelliteField": AUTHENTICATED,
    "Query.satelliteAlerts": frozenset({CLIENT, ADMIN}),
    "Query.fieldNdviSummary": AUTHENTICATED,
    "Mutation.register": PUBLIC,
    "Mutation.login": PUBLIC,
    "Mutation.logout": AUTHENTICATED,
    "Mutation.updateProfile": AUTHENTICATED,
    "Mutation.applyForExpert": frozenset({CLIENT}),
    "Mutation.createRequest": frozenset({CLIENT}),
    "Mutation.uploadRequestPhoto": frozenset({CLIENT}),
    "Mutation.respondToRequest": frozenset({EXPERT}),
    "Mutation.selectExpert": frozenset({CLIENT}),
    "Mutation.cancelRequest": frozenset({CLIENT}),
    "Mutation.createPayment": frozenset({CLIENT}),
    "Mutation.requestWithdrawal": frozenset({EXPERT}),
    "Mutation.approveWithdrawal": frozenset({ADMIN}),
    "Mutation.createDiagnosis": frozenset({EXPERT}),
    "Mutation.addTreatmentStep": frozenset({EXPERT}),
    "Mutation.uploadTrackerPhoto": frozenset({CLIENT}),
    "Mutation.updateTreatment": frozenset({EXPERT}),
    "Mutation.completeTracker": frozenset({EXPERT}),
    "Mutation.sendMessage": AUTHENTICATED,
    "Mutation.markMessageRead": AUTHENTICATED,
    "Mutation.createVideoRoom": frozenset({EXPERT}),
    "Mutation.markNotificationRead": AUTHENTICATED,
    "Mutation.markAllNotificationsRead": AUTHENTICATED,
    "Mutation.verifyExpert": frozenset({ADMIN}),
    "Mutation.blockUser": frozenset({ADMIN}),
    "Mutation.createField": frozenset({CLIENT}),
}


def describe(rule) -> str:
    if rule == PUBLIC:
        return "без входа"
    if rule == AUTHENTICATED:
        return "любая роль"
    return ", ".join(sorted(rule))
