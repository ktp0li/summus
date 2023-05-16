from aiogram.filters.state import StatesGroup, State


class GlobalState(StatesGroup):
    NOT_AUTHORIZED = State()
    DEFAULT = State()
