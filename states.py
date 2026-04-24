from aiogram.fsm.state import StatesGroup, State

class BookingForm(StatesGroup):
    service = State()
    master = State()
    date = State()
    time = State()
    name = State()
    phone = State()
    confirm = State()
