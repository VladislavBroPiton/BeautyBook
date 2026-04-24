import asyncio
import logging
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from config import BOT_TOKEN, ADMIN_ID, CALENDAR_ID
from database import Database
from google_calendar import GoogleCalendarManager
from keyboards import service_keyboard, master_keyboard, confirm_keyboard, cancel_keyboard
from states import BookingForm

# Настройка логирования (чтобы видеть, что происходит)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация базы данных
db = Database()

# Инициализация Google Calendar
calendar_manager = GoogleCalendarManager(CALENDAR_ID)

# --- Хендлеры базовых команд ---

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    await db.add_user(user_id, username)
    await state.clear()  # Сбрасываем состояние, на случай если оно было

    await message.answer(
        f"Приветствую, {message.from_user.first_name}! 👋\n\n"
        "Я бот для записи в салон красоты 'BeautyBook'.\n"
        "Чем могу помочь?",
        reply_markup=service_keyboard  # Показываем услуги
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда для администратора: показать все записи."""
    if message.from_user.id == ADMIN_ID:
        appointments = await db.get_all_appointments()
        if not appointments:
            await message.answer("Записей пока нет.")
            return

        text = "*Текущие записи:*\n\n"
        for app in appointments:
            text += (f"👤 Клиент: {app['client_name']} (@{app['username']})\n"
                     f"💅 Услуга: {app['service']}\n"
                     f"👩‍🦰 Мастер: {app['master']}\n"
                     f"📅 Дата: {app['appointment_date']} в {app['appointment_time']}\n"
                     f"__________________________________\n")
        await message.answer(text, parse_mode="Markdown")

# --- Хендлеры процесса записи (FSM) ---

@dp.message(F.text.in_({"💅 Маникюр", "🦶 Педикюр"}))
async def service_chosen(message: Message, state: FSMContext):
    """Шаг 1: Выбрана услуга."""
    await state.update_data(service=message.text)
    await state.set_state(BookingForm.master)
    await message.answer("Выберите мастера:", reply_markup=master_keyboard)

@dp.message(BookingForm.master, F.text.in_({"👩‍🦰 Анна", "👩 Елена"}))
async def master_chosen(message: Message, state: FSMContext):
    """Шаг 2: Выбран мастер."""
    await state.update_data(master=message.text)
    await state.set_state(BookingForm.date)

    # Отправляем календарь для выбора даты (завтра + 14 дней)
    # Реализуйте свою логику или используйте готовую библиотеку aiogram-calendar
    await message.answer("Выберите дату визита:", reply_markup=cancel_keyboard)

@dp.message(BookingForm.date)
async def date_chosen(message: Message, state: FSMContext):
    """Шаг 3: Выбрана дата (в примере - просто текст)."""
    date_str = message.text.strip()
    # Проверка формата даты (DD.MM.YYYY)
    if not re.match(r'\d{2}\.\d{2}\.\d{4}', date_str):
        await message.answer("Пожалуйста, введите дату в формате **ДД.ММ.ГГГГ**.\nПример: `25.12.2025`", parse_mode="Markdown")
        return

    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y").date()
        await state.update_data(date=date_obj)
        await state.set_state(BookingForm.time)

        # Логика получения свободного времени
        user_data = await state.get_data()
        master = user_data.get("master")
        busy_times = await db.get_appointments_for_date(date_str, master)  # busy_times = ['10:00', '14:30']

        # Формируем клавиатуру со временем
        time_keyboard = []
        for hour in range(9, 20):  # С 9 утра до 8 вечера
            for minute in [0, 30]:  # С шагом в 30 минут
                slot = f"{hour:02d}:{minute:02d}"
                if slot in busy_times:  # Пропускаем занятые слоты
                    continue
                # ... (добавьте логику создания кнопок в time_keyboard)

        await message.answer(f"Отлично! На {date_str} свободные слоты: (Здесь будет клавиатура со временем)", reply_markup=...)
    except ValueError:
        await message.answer("Некорректная дата. Пожалуйста, используйте формат **ДД.ММ.ГГГГ**.", parse_mode="Markdown")

@dp.message(BookingForm.time)
async def time_chosen(message: Message, state: FSMContext):
    """Шаг 4: Выбрано время."""
    await state.update_data(time=message.text)
    await state.set_state(BookingForm.name)
    await message.answer("Введите ваше имя:", reply_markup=cancel_keyboard)

@dp.message(BookingForm.name)
async def name_chosen(message: Message, state: FSMContext):
    """Шаг 5: Введено имя."""
    await state.update_data(name=message.text)
    await state.set_state(BookingForm.phone)
    await message.answer("Введите ваш номер телефона:")

@dp.message(BookingForm.phone)
async def phone_chosen(message: Message, state: FSMContext):
    """Шаг 6: Введен телефон."""
    phone = message.text.strip()
    # Простейшая проверка номера телефона
    phone_pattern = r'^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$'
    if not re.match(phone_pattern, phone):
        await message.answer("Пожалуйста, введите корректный номер телефона.")
        return

    await state.update_data(phone=phone)
    user_data = await state.get_data()
    await state.set_state(BookingForm.confirm)

    confirmation_text = (f"📝 *Пожалуйста, проверьте данные:*\n\n"
                         f"💅 Услуга: {user_data['service']}\n"
                         f"👩‍🦰 Мастер: {user_data['master']}\n"
                         f"📅 Дата: {user_data['date']} в {user_data['time']}\n"
                         f"👤 Имя: {user_data['name']}\n"
                         f"📞 Телефон: {user_data['phone']}\n\n"
                         f"Всё верно?")
    await message.answer(confirmation_text, reply_markup=confirm_keyboard, parse_mode="Markdown")

@dp.callback_query(BookingForm.confirm, F.data == "confirm_yes")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    """Подтверждение записи."""
    user_data = await state.get_data()
    user_id = callback.from_user.id

    # 1. Сохраняем запись в базу данных
    appointment_id = await db.add_appointment(
        user_id=user_id,
        service=user_data['service'],
        master=user_data['master'],
        date=user_data['date'],
        time=user_data['time'],
        name=user_data['name'],
        phone=user_data['phone']
    )
    logger.info(f"Новая запись #{appointment_id} от {user_data['name']}")

    # 2. Добавляем событие в Google Календарь
    event_link = await calendar_manager.create_event(
        summary=f"Запись в салон: {user_data['service']}",
        description=f"Клиент: {user_data['name']}, Телефон: {user_data['phone']}",
        start_time=f"{user_data['date']}T{user_data['time']}:00",
        end_time=f"{user_data['date']}T{user_data['time']}:00" # Пока длительность 1 час. Можно настроить.
    )

    # 3. Отправляем подтверждение клиенту
    await callback.message.edit_text(f"✅ Запись подтверждена!\n\n"
                                     f"Мы ждем вас {user_data['date']} в {user_data['time']}.\n"
                                     f"До встречи!",
                                     reply_markup=None)
    await state.clear()

    # 4. Уведомляем администратора в служебный чат
    await bot.send_message(ADMIN_ID,
                           f"🆕 *Новая запись!*\n"
                           f"ID записи: #{appointment_id}\n"
                           f"Клиент: {user_data['name']}\n"
                           f"Услуга: {user_data['service']}\n"
                           f"Дата и время: {user_data['date']} {user_data['time']}\n"
                           f"Ссылка в Google Calendar: {event_link}",
                           parse_mode="Markdown")

@dp.callback_query(BookingForm.confirm, F.data == "confirm_no")
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    """Отмена записи и перезапуск."""
    await callback.message.edit_text("Хорошо, давайте начнем заново. Выберите услугу из меню ниже.",
                                     reply_markup=service_keyboard)
    await state.clear()

# Хендлер для кнопки отмены
@dp.message(F.text == "🚫 Отменить действие", StateFilter(BookingForm))
async def cancel_action(message: Message, state: FSMContext):
    """Отмена текущего действия."""
    await state.clear()
    await message.answer("Действие отменено. Выберите услугу для записи.", reply_markup=service_keyboard)

# --- Запуск бота ---
async def main():
    # Создаем DSN для подключения к PostgreSQL
    DSN = "postgresql://user:password@localhost/beautybook"  # ЗАМЕНИТЕ НА СВОИ ДАННЫЕ!
    await db.create_pool(DSN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
