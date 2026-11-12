from .grpc_support import request_args, rpc
from .proto import auth_pb2 as pb, auth_pb2_grpc as pb_grpc


class AuthServicer(pb_grpc.AuthServiceServicer):
    def __init__(self, service, sessions):
        self.s, self.sessions = service, sessions

    @rpc(pb.ValidateUserResponse)
    def ValidateUser(self, request, context):
        return self.s.validate_user(request.user_id)

    @rpc(pb.UserResponse)
    def GetUser(self, request, context):
        return self.s.get_user(request.user_id)

    @rpc(pb.GetUsersResponse)
    def GetUsers(self, request, context):
        return {"users": self.s.list_users(**request_args(request))}

    @rpc(pb.UserResponse)
    def Register(self, request, context):
        return self.s.register(request.email, request.password, request.name)

    @rpc(pb.AuthResponse)
    def Login(self, request, context):
        data = self.sessions.login(request.email, request.password)
        return {"token": data["access_token"], "user": data["user"], "expires_in": data["expires_in"],
                "session_id": data["session_id"], "token_type": data["token_type"]}

    @rpc(pb.UserResponse)
    def UpdateProfile(self, request, context):
        return self.s.update_profile(**request_args(request))

    @rpc(pb.IdentityResponse)
    def VerifyToken(self, request, context):
        return self.sessions.verify(request.token)

    @rpc(pb.LogoutResponse)
    def Logout(self, request, context):
        return {"revoked": self.sessions.logout(request.token)}

    @rpc(pb.UserResponse)
    def AssignRole(self, request, context):
        return self.s.assign_role(request.user_id, request.role)

    @rpc(pb.SetUserStatusResponse)
    def SetUserStatus(self, request, context):
        user = self.s.set_status(request.user_id, request.status)
        revoked = self.sessions.revoke_user_sessions(request.user_id) if request.status != "ACTIVE" else 0
        return {"user": user, "revoked_sessions": revoked}

    @rpc(pb.UsersSummaryResponse)
    def GetUsersSummary(self, request, context):
        return self.s.users_summary()


def registration(service):
    servicer = AuthServicer(service, service.session_manager)
    return ([lambda server: pb_grpc.add_AuthServiceServicer_to_server(servicer, server)],
            [pb.DESCRIPTOR.services_by_name["AuthService"].full_name])
