from aiogram.fsm.state import State, StatesGroup


class WalletStates(StatesGroup):
    waiting_for_wallet = State()


class DealCreationStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_description = State()
    waiting_for_currency = State()
    waiting_for_amount = State()


class ChannelDealStates(StatesGroup):
    """Input state isolated from the generic offer creation flow."""

    waiting_for_channel = State()


class DisputeStates(StatesGroup):
    waiting_for_description = State()


class AdminStates(StatesGroup):
    waiting_for_resolution_reason = State()
    waiting_for_broadcast = State()
    waiting_for_maintenance_message = State()
