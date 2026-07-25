from decimal import Decimal


class ApplicationError(RuntimeError):
    """Base error safe for application-layer handling."""


class DealNotFoundError(ApplicationError):
    pass


class InvalidWalletError(ApplicationError):
    pass


class UnsupportedCurrencyError(ApplicationError):
    pass


class TonGatewayError(ApplicationError):
    pass


class MissingPayoutWalletError(ApplicationError):
    pass


class DealConfirmationForbiddenError(ApplicationError):
    pass


class DealAmountTooSmallError(ApplicationError):
    def __init__(self, minimum: Decimal):
        self.minimum = minimum
        super().__init__(f"Deal amount must be at least {minimum} TON")


class InsufficientPayoutReserveError(ApplicationError):
    pass
