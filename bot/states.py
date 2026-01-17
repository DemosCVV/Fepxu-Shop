from aiogram.fsm.state import State, StatesGroup


class TopUp(StatesGroup):
    waiting_amount = State()


class AdminBroadcast(StatesGroup):
    waiting_text = State()


class AdminGrant(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()
