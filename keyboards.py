from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Клавиатура для выбора услуги
service_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💅 Маникюр")],
        [KeyboardButton(text="🦶 Педикюр")],
    ],
    resize_keyboard=True
)

# Клавиатура для подтверждения записи
confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Да, всё верно", callback_data="confirm_yes")],
    [InlineKeyboardButton(text="❌ Нет, начать заново", callback_data="confirm_no")]
])

# Клавиатура для выбора мастера
master_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👩‍🦰 Анна")],
        [KeyboardButton(text="👩 Елена")]
    ],
    resize_keyboard=True
)

# Клавиатура для отмены действия
cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🚫 Отменить действие")]],
    resize_keyboard=True
)
