from aiogram.fsm.state import State, StatesGroup


class WalletStates(StatesGroup):
    waiting_for_wallet = State()


class DealCreationStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_description = State()
    waiting_for_currency = State()
    waiting_for_amount = State()

