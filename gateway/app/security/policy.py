from .identity import ADMIN, CLIENT, EXPERT

PUBLIC = "PUBLIC"
AUTHENTICATED = "AUTHENTICATED"

POLICY: dict = {
    "Query.me": AUTHENTICATED,
    "Query.user": AUTHENTICATED,                         # объект: свой профиль или администратор
    "Query.users": frozenset({ADMIN}),
    "Query.usersSummary": frozenset({ADMIN}),
    "Query.request": AUTHENTICATED,                      # объект: автор, назначенный эксперт, админ; очередь — эксперты
    "Query.myRequests": frozenset({CLIENT}),
    "Query.availableRequests": frozenset({EXPERT, ADMIN}),
    "Query.requestsByExpert": frozenset({EXPERT, ADMIN}),    # область: эксперт видит только свои
    "Query.requestsSummary": AUTHENTICATED,              # область: данные ограничиваются ролью
    "Query.diagnosis": AUTHENTICATED,                    # объект: участники заявки и админ
    "Query.diagnosisByRequest": AUTHENTICATED,
    "Query.responsesSummary": frozenset({EXPERT, ADMIN}),    # область: эксперт — только свои
    "Query.tracker": AUTHENTICATED,                      # объект: участники заявки и админ
    "Query.trackerByRequest": AUTHENTICATED,
    "Query.trackerProgress": AUTHENTICATED,
    "Query.chatRoom": AUTHENTICATED,                     # объект: только участники чата
    "Query.chatRoomByRequest": AUTHENTICATED,
    "Query.chatUnreadCount": AUTHENTICATED,
    "Query.notifications": AUTHENTICATED,                # всегда свои
    "Query.notificationsSummary": AUTHENTICATED,
    "Query.transactions": AUTHENTICATED,                 # область: клиент — свои платежи, эксперт — по своим заявкам
    "Query.transactionsSummary": AUTHENTICATED,
    "Query.withdrawals": frozenset({EXPERT, ADMIN}),         # область: эксперт — только свои
    "Query.expertBalance": frozenset({EXPERT, ADMIN}),       # область: эксперт — только свой
    "Query.expertApplications": frozenset({ADMIN}),
    "Query.applicationsSummary": frozenset({ADMIN}),
    "Query.expertStats": frozenset({EXPERT, ADMIN}),         # область: эксперт — только своя
    "Query.topExperts": AUTHENTICATED,
    "Query.diseaseStats": AUTHENTICATED,
    "Query.platformSummary": frozenset({ADMIN}),
    "Query.myFields": frozenset({CLIENT}),
    "Query.satelliteField": AUTHENTICATED,               # объект: владелец или админ
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
    "Mutation.sendMessage": AUTHENTICATED,               # объект: только участники чата
    "Mutation.markMessageRead": AUTHENTICATED,
    "Mutation.createVideoRoom": frozenset({EXPERT}),
    "Mutation.markNotificationRead": AUTHENTICATED,      # объект: только своё уведомление
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
