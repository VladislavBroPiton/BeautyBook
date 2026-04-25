import asyncio
import logging
import re
import os
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID, CALENDAR_ID
from database import Database
from google_calendar import GoogleCalendarManager
from keyboards import service_keyboard, confirm_keyboard, cancel_keyboard
from states import BookingForm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()
calendar_manager = GoogleCalendarManager(CALENDAR_ID)

# ---------- Веб-сервер для Render и статики ----------
async def handle_health(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_health)
    # Раздаём папку webapp по адресу /webapp/
    app.router.add_static('/webapp/', path='webapp/', show_index=True)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    logger.info("✅ Веб-сервер запущен: health check + статика /webapp/")

# ---------- Команды бота ----------
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    await db.add_user(user_id, username)
    await state.clear()
    # Клавиатура с кнопкой открытия Mini App
    web_app_url = os.getenv("WEBAPP_URL", "https://beautybook-bot.onrender.com/webapp/")
    web_app_button = KeyboardButton(text="📱 Записаться через приложение", web_app=web_app_url)
    keyboard = ReplyKeyboardMarkup(keyboard=[[web_app_button]], resize_keyboard=True)
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я бот салона BeautyBook. Нажми на кнопку ниже, чтобы открыть удобную форму записи.",
        reply_markup=keyboard
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id == ADMIN_ID:
        appointments = await db.get_all_appointments()
        if not appointments:
            await message.answer("Записей пока нет.")
            return
        text = "*Текущие записи:*\\n"
        for app in appointments:
            text += (f"👤 {app['client_name']} (@{app['username']})\n"
                     f"💅 {app['service']} | 👩‍🦰 {app['master']}\n"
                     f"📅 {app['appointment_date']} {app['appointment_time']}\n"
                     f"__________________________________\n")
        await message.answer(text, parse_mode="Markdown")

# ---------- Обработка данных из Mini App ----------
@dp.message(F.web_app_data)
async def handle_web_app_data(message: Message, state: FSMContext):
    data = json.loads(message.web_app_data.data)
    user_id = message.from_user.id

    # Разбираем дату и время из строки вида "2025-12-25T15:30"
    datetime_str = data['datetime']
    date_part = datetime_str.split('T')[0]
    time_part = datetime_str.split('T')[1]

    # Сохраняем запись
    appointment_id = await db.add_appointment(
        user_id=user_id,
        service=data['service'],
        master=data['master'],
        date=date_part,
        time=time_part,
        name=data['name'],
        phone=data['phone']
    )
    logger.info(f"Новая запись #{appointment_id} от {data['name']}")

    # Google Calendar
    try:
        event_link = await calendar_manager.create_event(
            summary=f"Запись в салон: {data['service']}",
            description=f"Клиент: {data['name']}, Тел.: {data['phone']}",
            start_time=f"{date_part}T{time_part}:00",
            end_time=f"{date_part}T{time_part}:00"
        )
    except Exception as e:
        logger.error(f"Calendar error: {e}")
        event_link = "Ошибка создания события"

    await message.answer(f"✅ Запись подтверждена!\n\nМы ждём вас {date_part} в {time_part}.\nДо встречи!")
    await bot.send_message(
        ADMIN_ID,
        f"🆕 *Новая запись!*\n"
        f"ID: #{appointment_id}\n"
        f"Клиент: {data['name']}\n"
        f"Услуга: {data['service']}\n"
        f"Мастер: {data['master']}\n"
        f"Дата и время: {date_part} {time_part}\n"
        f"Календарь: {event_link}",
        parse_mode="Markdown"
    )

# ---------- Обработчики старых кнопок (на случай, если кто-то нажмёт) ----------
@dp.message(F.text.in_({"💅 Маникюр", "🦶 Педикюр"}))
async def service_chosen(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, используйте кнопку «Записаться через приложение» в меню.")

@dp.message(F.text == "🚫 Отменить действие", StateFilter(BookingForm))
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено. Используйте главную кнопку для записи.", reply_markup=service_keyboard)

# ---------- Запуск ----------
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    DSN = os.getenv("DATABASE_URL")
    if not DSN:
        raise ValueError("DATABASE_URL missing")
    await db.create_pool(DSN)
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
