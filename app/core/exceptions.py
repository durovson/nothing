from decimal import Decimal


class ApplicationError(RuntimeError):
    """Base error safe for application-layer handling."""


class DealNotFoundError(ApplicationError):
    pass


class InvalidWalletError(ApplicationError):
    pass


class TonGatewayError(ApplicationError):
    pass


class MissingPayoutWalletError(ApplicationError):
    pass


class MissingLinkedWalletError(ApplicationError):
    pass


class DealConfirmationForbiddenError(ApplicationError):
    pass


class DealActionForbiddenError(ApplicationError):
    pass


class DealAmountTooSmallError(ApplicationError):
    def __init__(self, minimum: Decimal, currency: object = "TON"):
        self.minimum = minimum
        self.currency = currency
        super().__init__(f"Deal amount must be at least {minimum} {currency}")


class InsufficientPayoutReserveError(ApplicationError):
    pass


class ReferralWithdrawalError(ApplicationError):
    pass
