import asyncio
import logging
import os
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID, CALENDAR_ID
from database import Database
from google_calendar import GoogleCalendarManager

# ---------- Настройка логов ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Инициализация бота и диспетчера ----------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()
calendar_manager = GoogleCalendarManager(CALENDAR_ID)

# ---------- Список менеджеров (Telegram ID) ----------
MANAGER_IDS = list(map(int, os.getenv("MANAGER_IDS", "").split(","))) if os.getenv("MANAGER_IDS") else []
# Словарь для пагинации записей менеджера (user_id -> {apps, index})
user_pagination = {}

# ---------- Сопоставление имени мастера и его Telegram ID ----------
MASTER_IDS = {
    "👩‍🦰 Анна": 458433916,      # Замените на реальный Telegram ID Анны
    "👩 Елена": 987654321,      # ID Елены
    "👩‍🦱 Наталья": 555555555,   # ID Натальи (если есть)
}

# ---------- Команда /start ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    await db.add_user(user_id, username)

    web_app_url = os.getenv("WEBAPP_URL", "https://beautybook-bot.onrender.com/webapp/")
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="📱 Записаться через приложение", web_app=types.WebAppInfo(url=web_app_url))]],
        resize_keyboard=True
    )
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\nНажми на кнопку ниже, чтобы записаться.",
        reply_markup=keyboard
    )

# ---------- Команда /admin (только для владельца) ----------
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    appointments = await db.get_all_appointments()
    if not appointments:
        await message.answer("Записей пока нет.")
        return
    text = "*Текущие записи (все):*\n"
    for app in appointments:
        text += (f"👤 {app['client_name']} (@{app['username']})\n"
                 f"💅 {app['service']} | 👩‍🦰 {app['master']}\n"
                 f"📅 {app['appointment_date']} {app['appointment_time']}\n"
                 "──────────────────\n")
    await message.answer(text, parse_mode="Markdown")

# ---------- Команда /my для менеджеров (просмотр своих записей) ----------
@dp.message(Command("my"))
async def show_my_appointments(message: types.Message):
    user_id = message.from_user.id
    if user_id not in MANAGER_IDS:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    appointments = await db.get_appointments_by_master_telegram_id(user_id)
    if not appointments:
        await message.answer("У вас пока нет записей.")
        return

    user_pagination[user_id] = {
        "apps": appointments,
        "index": 0
    }
    await send_appointment_card(message, user_id, 0)

async def send_appointment_card(message: types.Message, user_id: int, idx: int):
    data = user_pagination.get(user_id)
    if not data or idx >= len(data["apps"]):
        return
    app = data["apps"][idx]
    text = (f"🆔 *Запись #{app['id']}*\n\n"
            f"👤 Клиент: {app['client_name']}\n"
            f"📞 Телефон: {app['client_phone']}\n"
            f"💅 Услуга: {app['service']}\n"
            f"📅 Дата: {app['appointment_date']}\n"
            f"⏰ Время: {app['appointment_time']}\n")
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel_{app['id']}")],
        [
            types.InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{idx}"),
            types.InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"next_{idx}")
        ]
    ])
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith(("prev_", "next_", "cancel_")))
async def handle_pagination(callback: types.CallbackQuery):
    action, val = callback.data.split("_", 1)
    user_id = callback.from_user.id
    data = user_pagination.get(user_id)
    if not data:
        await callback.answer("Сессия устарела, начните заново с /my", show_alert=True)
        return

    if action == "prev":
        new_idx = max(0, int(val)-1)
        data["index"] = new_idx
        await callback.message.delete()
        await send_appointment_card(callback.message, user_id, new_idx)
    elif action == "next":
        new_idx = min(len(data["apps"])-1, int(val)+1)
        data["index"] = new_idx
        await callback.message.delete()
        await send_appointment_card(callback.message, user_id, new_idx)
    elif action == "cancel":
        app_id = int(val)
        app = await db.get_appointment_by_id(app_id)
        if not app or app["master_telegram_id"] != user_id:
            await callback.answer("Нет прав для отмены этой записи", show_alert=True)
            return
        await db.delete_appointment(app_id)
        await callback.answer("Запись отменена", show_alert=True)
        # Обновляем список записей
        new_apps = await db.get_appointments_by_master_telegram_id(user_id)
        if not new_apps:
            await callback.message.edit_text("У вас больше нет записей.")
            user_pagination.pop(user_id, None)
            return
        data["apps"] = new_apps
        data["index"] = min(data["index"], len(new_apps)-1)
        await callback.message.delete()
        await send_appointment_card(callback.message, user_id, data["index"])
    await callback.answer()

# ---------- Обработка данных из Mini App ----------
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    user_id = message.from_user.id
    datetime_str = data['datetime']
    date_part = datetime_str.split('T')[0]
    time_part = datetime_str.split('T')[1]

    master_name = data['master']
    master_tg_id = MASTER_IDS.get(master_name)

    appointment_id = await db.add_appointment(
        user_id=user_id,
        service=data['service'],
        master=master_name,
        date=date_part,
        time=time_part,
        name=data['name'],
        phone=data['phone'],
        master_telegram_id=master_tg_id
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
        event_link = "Ошибка создания события"

    await message.answer(f"✅ Запись подтверждена!\n\nЖдём вас {date_part} в {time_part}.\nДо встречи!")
    await bot.send_message(
        ADMIN_ID,
        f"🆕 *Новая запись!*\n"
        f"ID: #{appointment_id}\n"
        f"Клиент: {data['name']}\n"
        f"Услуга: {data['service']}\n"
        f"Мастер: {master_name}\n"
        f"Дата и время: {date_part} {time_part}\n"
        f"Календарь: {event_link}",
        parse_mode="Markdown"
    )

# ---------- Вебхук и статика ----------
async def handle_webhook(request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(status=200)

async def handle_health(request):
    return web.Response(text="OK")

async def webapp_index(request):
    return web.FileResponse('webapp/index.html')

# ---------- Запуск ----------
async def main():
    # Удаляем предыдущие вебхуки
    await bot.delete_webhook(drop_pending_updates=True)

    DSN = os.getenv("DATABASE_URL")
    if not DSN:
        raise ValueError("DATABASE_URL missing")
    await db.create_pool(DSN)

    app = web.Application()
    app.router.add_get('/health', handle_health)
    app.router.add_post('/webhook', handle_webhook)
    app.router.add_get('/webapp/', webapp_index)
    app.router.add_static('/webapp/static', path='webapp/', show_index=False)

    port = int(os.environ.get("PORT", 8000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Веб-сервер запущен на порту {port}")

    webhook_url = f"https://beautybook-bot.onrender.com/webhook"
    await bot.set_webhook(url=webhook_url)
    logger.info(f"✅ Вебхук установлен: {webhook_url}")

    # Бесконечное ожидание (чтобы процесс не завершался)
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
