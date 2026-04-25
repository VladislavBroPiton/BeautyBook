import asyncio
import logging
import os
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Update, WebAppInfo
from aiohttp import web
from aiogram import Dispatcher, types, F   # F обязательно

from config import BOT_TOKEN, ADMIN_ID, CALENDAR_ID
from database import Database
from google_calendar import GoogleCalendarManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()
calendar_manager = GoogleCalendarManager(CALENDAR_ID)

# ---------- Хендлеры команд ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    await db.add_user(user_id, username)
    web_app_url = os.getenv("WEBAPP_URL", "https://beautybook-bot.onrender.com/webapp/")
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="📱 Записаться через приложение", web_app=WebAppInfo(url=web_app_url))]],
        resize_keyboard=True
    )
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\nНажми на кнопку ниже, чтобы записаться.",
        reply_markup=keyboard
    )

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    appointments = await db.get_all_appointments()
    if not appointments:
        await message.answer("Записей пока нет.")
        return
    text = "*Текущие записи:*\n"
    for app in appointments:
        text += (f"👤 {app['client_name']} (@{app['username']})\n"
                 f"💅 {app['service']} | 👩‍🦰 {app['master']}\n"
                 f"📅 {app['appointment_date']} {app['appointment_time']}\n"
                 "__________________________________\n")
    await message.answer(text, parse_mode="Markdown")

@dp.message(types.WebAppData)
async def handle_web_app_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    user_id = message.from_user.id
    datetime_str = data['datetime']
    date_part = datetime_str.split('T')[0]
    time_part = datetime_str.split('T')[1]

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

    try:
        event_link = await calendar_manager.create_event(
            summary=f"Запись в салон: {data['service']}",
            description=f"Клиент: {data['name']}, Тел.: {data['phone']}",
            start_time=f"{date_part}T{time_part}:00",
            end_time=f"{date_part}T{time_part}:00"
        )
    except Exception as e:
        logger.error(f"Calendar error: {e}")
        event_link = "Ошибка"

    await message.answer(f"✅ Запись подтверждена!\n\nЖдём вас {date_part} в {time_part}.\nДо встречи!")
    await bot.send_message(
        ADMIN_ID,
        f"🆕 *Новая запись!*\nID: #{appointment_id}\nКлиент: {data['name']}\nУслуга: {data['service']}\nМастер: {data['master']}\nДата и время: {date_part} {time_part}\nКалендарь: {event_link}",
        parse_mode="Markdown"
    )

# ---------- Webhook ----------
async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(status=200)

async def handle_health(request):
    return web.Response(text="OK")

# ---------- Запуск ----------
async def main():
    # Удаляем старые вебхуки и сбрасываем pending updates
    await bot.delete_webhook(drop_pending_updates=True)

    DSN = os.getenv("DATABASE_URL")
    if not DSN:
        raise ValueError("DATABASE_URL missing")
    await db.create_pool(DSN)

    app = web.Application()
    app.router.add_get('/health', handle_health)
    app.router.add_post('/webhook', handle_webhook)
    app.router.add_static('/webapp/', path='webapp/', show_index=True)

    port = int(os.environ.get("PORT", 8000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Веб-сервер запущен на порту {port}")

    webhook_url = f"https://beautybook-bot.onrender.com/webhook"
    await bot.set_webhook(url=webhook_url)
    logger.info(f"✅ Вебхук установлен: {webhook_url}")

    # Бесконечное ожидание, чтобы процесс не завершился
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
