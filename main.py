import os
import json
import logging
from datetime import datetime

from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.requests import Request
from starlette.routing import Route
import uvicorn

from telegram import Update
from telegram.ext import Application, ContextTypes

from config import BOT_TOKEN, ADMIN_ID, CALENDAR_ID
from database import Database
from google_calendar import GoogleCalendarManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация компонентов
db = Database()
calendar_manager = GoogleCalendarManager(CALENDAR_ID)

async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    await db.add_user(user_id, username)

    web_app_url = os.getenv("WEBAPP_URL", "https://beautybook-bot.onrender.com/webapp/")
    keyboard = [[{
        "text": "📱 Записаться через приложение",
        "web_app": {"url": web_app_url}
    }]]
    reply_markup = {"keyboard": keyboard, "resize_keyboard": True}
    
    await update.message.reply_text(
        f"Привет, {update.effective_user.first_name}! 👋\n\n"
        "Нажми на кнопку ниже, чтобы записаться.",
        reply_markup=reply_markup
    )

async def handle_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /admin"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    appointments = await db.get_all_appointments()
    if not appointments:
        await update.message.reply_text("Записей пока нет.")
        return
    
    text = "*Текущие записи:*\n"
    for app in appointments:
        text += (f"👤 {app['client_name']} (@{app['username']})\n"
                 f"💅 {app['service']} | 👩‍🦰 {app['master']}\n"
                 f"📅 {app['appointment_date']} {app['appointment_time']}\n"
                 "__________________________________\n")
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка данных из Mini App"""
    data = json.loads(update.message.web_app_data.data)
    user_id = update.effective_user.id

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

    await update.message.reply_text(
        f"✅ Запись подтверждена!\n\nЖдём вас {date_part} в {time_part}.\nДо встречи!"
    )
    await context.bot.send_message(
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

# Настройка handlers
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", handle_start_command))
application.add_handler(CommandHandler("admin", handle_admin_command))
application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

# ---- ASGI приложение ----
async def healthcheck(request: Request):
    """Эндпоинт для проверки работоспособности"""
    return PlainTextResponse("OK")

async def webhook(request: Request):
    """Основной эндпоинт для получения обновлений от Telegram"""
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse({"status": "error"}, status_code=500)

# Создание ASGI приложения Starlette
routes = [
    Route("/healthcheck", endpoint=healthcheck, methods=["GET"]),
    Route("/webhook", endpoint=webhook, methods=["POST"]),
]
starlette_app = Starlette(routes=routes)

# ---- Точка входа для сервера ----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)
