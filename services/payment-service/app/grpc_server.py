from .grpc_support import request_args, rpc
from .proto import payment_pb2 as pb, payment_pb2_grpc as pb_grpc
from .utils import parse_dt_bound


class PaymentServicer(pb_grpc.PaymentServiceServicer):
    def __init__(self, service):
        self.s = service

    @staticmethod
    def _dates(args: dict) -> dict:
        args["created_from"] = parse_dt_bound(args.get("created_from"))
        args["created_to"] = parse_dt_bound(args.get("created_to"), upper=True)
        return args

    @rpc(pb.PaymentResponse)
    def CreatePayment(self, request, context):
        return self.s.create_payment(**request_args(request))

    @rpc(pb.PaymentResponse)
    def GetTransaction(self, request, context):
        return self.s.get_transaction(request.transaction_id)

    @rpc(pb.ListTransactionsResponse)
    def ListTransactions(self, request, context):
        return {"transactions": self.s.list_transactions(**self._dates(request_args(request)))}

    @rpc(pb.TransactionsSummaryResponse)
    def GetTransactionsSummary(self, request, context):
        return self.s.transactions_summary(**request_args(request))

    @rpc(pb.BalanceResponse)
    def GetBalance(self, request, context):
        return self.s.expert_balance(request.expert_id)

    @rpc(pb.WithdrawalResponse)
    def RequestWithdrawal(self, request, context):
        return self.s.request_withdrawal(**request_args(request))

    @rpc(pb.WithdrawalResponse)
    def ApproveWithdrawal(self, request, context):
        return self.s.approve_withdrawal(**request_args(request))

    @rpc(pb.ListWithdrawalsResponse)
    def ListWithdrawals(self, request, context):
        return {"withdrawals": self.s.list_withdrawals(**request_args(request))}


def registration(service):
    servicer = PaymentServicer(service)
    return ([lambda server: pb_grpc.add_PaymentServiceServicer_to_server(servicer, server)],
            [pb.DESCRIPTOR.services_by_name["PaymentService"].full_name])
