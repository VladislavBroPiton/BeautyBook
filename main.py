import asyncio
import logging
import os
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID, CALENDAR_ID
from database import Database
from google_calendar import GoogleCalendarManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()
calendar_manager = GoogleCalendarManager(CALENDAR_ID)

MANAGER_IDS = list(map(int, os.getenv("MANAGER_IDS", "").split(","))) if os.getenv("MANAGER_IDS") else []
user_pagination = {}

PRICES = {
    "💅 Маникюр": 2500,
    "🦶 Педикюр": 3500,
    "💆‍♀️ Спа-уход": 4000,
}

MASTER_IDS = {
    "👩‍🦰 Анна": 123456789,      # замените на реальные ID
    "👩 Елена": 987654321,
    "👩‍🦱 Наталья": 555555555,
}
DAILY_LIMIT = 5

# ---------- Команды ----------
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
        text += (f"🆔 {app['id']} - {app['client_name']} (@{app['username']})\n"
                 f"💅 {app['service']} | 👩‍🦰 {app['master']}\n"
                 f"📅 {app['appointment_date']} {app['appointment_time']}\n"
                 f"💰 {app['service_price']} руб.\n──────────────────\n")
    if len(text) > 4000:
        for part in [text[i:i+4000] for i in range(0, len(text), 4000)]:
            await message.answer(part, parse_mode="Markdown")
    else:
        await message.answer(text, parse_mode="Markdown")

@dp.message(Command("my_records"))
async def show_my_records(message: types.Message):
    user_id = message.from_user.id
    records = await db.get_appointments_by_user_id(user_id)
    if not records:
        await message.answer("У вас пока нет активных записей.")
        return
    for r in records:
        text = (f"🆔 *Запись #{r['id']}*\n"
                f"💅 {r['service']}\n"
                f"👩‍🦰 Мастер: {r['master']}\n"
                f"📅 {r['appointment_date']} в {r['appointment_time']}\n"
                f"💰 {r['service_price']} руб.\n")
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"user_cancel_{r['id']}")]
        ])
        await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("user_cancel_"))
async def user_cancel_appointment(callback: types.CallbackQuery):
    app_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    app = await db.get_appointment_by_id(app_id)
    if not app or app["user_id"] != user_id:
        await callback.answer("Запись не найдена или нет прав.", show_alert=True)
        return
    await db.delete_appointment(app_id)
    await callback.answer("Запись отменена", show_alert=True)
    await callback.message.edit_text(f"✅ Запись #{app_id} отменена.")

@dp.message(Command("my"))
async def show_my_appointments(message: types.Message):
    user_id = message.from_user.id
    if user_id not in MANAGER_IDS:
        await message.answer("⛔ У вас нет доступа.")
        return
    appointments = await db.get_appointments_by_master_telegram_id(user_id)
    if not appointments:
        await message.answer("У вас пока нет записей.")
        return
    user_pagination[user_id] = {"apps": appointments, "index": 0}
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
            f"💰 {app['service_price']} руб.\n"
            f"📅 Дата: {app['appointment_date']}\n"
            f"⏰ Время: {app['appointment_time']}\n")
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel_{app['id']}")],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{idx}"),
         types.InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"next_{idx}")]
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
            await callback.answer("Нет прав для отмены", show_alert=True)
            return
        await db.delete_appointment(app_id)
        await callback.answer("Запись отменена", show_alert=True)
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

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    total = await db.get_appointments_count()
    today = datetime.now().date()
    today_count = await db.get_appointments_count_for_date(today)
    by_service = await db.get_appointments_grouped_by_service()
    by_master = await db.get_appointments_grouped_by_master()
    text = (f"*📊 Статистика*\n\n"
            f"Всего записей: {total}\n"
            f"За сегодня: {today_count}\n\n"
            f"*По услугам:*\n" + "\n".join([f"{s['service']}: {s['count']}" for s in by_service]) + "\n\n"
            f"*По мастерам:*\n" + "\n".join([f"{m['master']}: {m['count']}" for m in by_master]))
    if len(text) > 4000:
        for part in [text[i:i+4000] for i in range(0, len(text), 4000)]:
            await message.answer(part, parse_mode="Markdown")
    else:
        await message.answer(text, parse_mode="Markdown")

# ---------- Обработка данных из Mini App ----------
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    user_id = message.from_user.id

    datetime_str = data.get('datetime', '').replace(' ', 'T')
    if 'T' not in datetime_str or len(datetime_str.split('T')) != 2:
        await message.answer("Ошибка: неверный формат даты. Попробуйте снова.")
        return
    date_part = datetime_str.split('T')[0]
    time_part = datetime_str.split('T')[1]

    master_name = data['master']
    master_tg_id = MASTER_IDS.get(master_name)
    if not master_tg_id:
        await message.answer("Ошибка: мастер не найден. Обновите приложение.")
        return

    # Проверка лимита записей на мастера в день
    if not await db.check_master_limit(master_tg_id, date_part, DAILY_LIMIT):
        await message.answer(f"Извините, у мастера {master_name} достигнут лимит на этот день ({DAILY_LIMIT}). Выберите другую дату.")
        return

    # Проверка, что конкретный слот ещё свободен
    if not await db.is_slot_available(master_tg_id, date_part, time_part):
        await message.answer("❌ Это время уже занято. Пожалуйста, выберите другой слот.")
        return

    service = data['service']
    price = PRICES.get(service, 0)

    appointment_id = await db.add_appointment(
        user_id=user_id,
        service=service,
        service_price=price,
        master=master_name,
        master_telegram_id=master_tg_id,
        date=date_part,
        time=time_part,
        name=data['name'],
        phone=data['phone']
    )
    logger.info(f"Новая запись #{appointment_id} от {data['name']}")

    try:
        event_link = await calendar_manager.create_event(
            summary=f"Запись в салон: {service}",
            description=f"Клиент: {data['name']}, Тел.: {data['phone']}",
            start_time=f"{date_part}T{time_part}:00",
            end_time=f"{date_part}T{time_part}:00"
        )
    except Exception as e:
        logger.error(f"Calendar error: {e}")
        event_link = "Ошибка создания события"

    await message.answer(f"✅ Запись подтверждена!\n\nЖдём вас {date_part} в {time_part}.\nСтоимость: {price} руб.")
    await bot.send_message(
        ADMIN_ID,
        f"🆕 *Новая запись!*\n"
        f"ID: #{appointment_id}\n"
        f"Клиент: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Услуга: {service} ({price} руб.)\n"
        f"Мастер: {master_name}\n"
        f"Дата и время: {date_part} {time_part}\n"
        f"Календарь: {event_link}",
        parse_mode="Markdown"
    )

# ---------- Эндпоинт для получения свободных слотов ----------
async def get_slots(request):
    master = request.query.get('master')
    date = request.query.get('date')
    if not master or not date:
        return web.json_response({"busy": []}, status=200)
    date_clean = date.split('T')[0] if 'T' in date else date.split(' ')[0]
    master_id = MASTER_IDS.get(master)
    if not master_id:
        return web.json_response({"busy": []})  # мастер не найден – считаем все слоты свободными
    busy_times = await db.get_busy_slots_for_master(master_id, date_clean)
    return web.json_response({"busy": busy_times})

# ---------- Напоминания ----------
async def reminders_loop():
    while True:
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        next_hour = now + timedelta(hours=1)
        today_str = now.strftime("%Y-%m-%d")
        tomorrow_str = tomorrow.strftime("%Y-%m-%d")
        next_hour_str = next_hour.strftime("%H:%M")

        day_appointments = await db.get_appointments_for_reminder(tomorrow_str, 'day')
        for app in day_appointments:
            try:
                await bot.send_message(app['user_id'], f"🔔 Напоминаем, что завтра в {app['appointment_time']} у вас запись на {app['service']}.")
                await db.mark_reminder_sent(app['id'], 'day')
            except Exception as e:
                logger.error(f"Reminder day: {e}")

        hour_appointments = await db.get_appointments_for_reminder(today_str, 'hour', next_hour_str)
        for app in hour_appointments:
            try:
                await bot.send_message(app['user_id'], f"🔔 Через час у вас запись на {app['service']} в {app['appointment_time']}.")
                await db.mark_reminder_sent(app['id'], 'hour')
            except Exception as e:
                logger.error(f"Reminder hour: {e}")

        await asyncio.sleep(60)

# ---------- Webhook и статика ----------
async def handle_webhook(request):
    try:
        data = await request.json()
        if not data:
            raise ValueError("Empty data")
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

async def main():
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
    app.router.add_get('/get_slots', get_slots)

    port = int(os.environ.get("PORT", 8000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Веб-сервер запущен на порту {port}")

    webhook_url = f"https://beautybook-bot.onrender.com/webhook"
    await bot.set_webhook(url=webhook_url)
    logger.info(f"✅ Вебхук установлен: {webhook_url}")

    asyncio.create_task(reminders_loop())

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
