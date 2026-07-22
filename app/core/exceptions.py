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
