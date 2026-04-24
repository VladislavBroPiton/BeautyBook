import asyncio
from datetime import datetime, timedelta
from database import Database

async def send_reminders(bot, db_pool):
    """Фоновая задача: каждую минуту проверяет и отправляет напоминания."""
    db = Database()
    db.pool = db_pool
    while True:
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        next_hour = now + timedelta(hours=1)

        # Форматируем даты для сравнения
        today_str = now.strftime("%Y-%m-%d")
        tomorrow_str = tomorrow.strftime("%Y-%m-%d")
        next_hour_str = next_hour.strftime("%H:%M")

        async with db.pool.acquire() as conn:
            # Напоминания за день
            reminders_day = await conn.fetch('''
                SELECT a.*, u.user_id FROM appointments a
                JOIN users u ON a.user_id = u.user_id
                WHERE a.appointment_date = $1 AND a.reminder_day_sent = FALSE
            ''', tomorrow_str)

            for app in reminders_day:
                await bot.send_message(app['user_id'], f"🔔 Напоминаем, что завтра в {app['appointment_time']} у вас запись на '{app['service']}'.")
                await conn.execute('UPDATE appointments SET reminder_day_sent = TRUE WHERE id = $1', app['id'])

            # Напоминания за час
            reminders_hour = await conn.fetch('''
                SELECT a.*, u.user_id FROM appointments a
                JOIN users u ON a.user_id = u.user_id
                WHERE a.appointment_date = $1 AND a.appointment_time <= $2 AND a.reminder_hour_sent = FALSE
            ''', today_str, next_hour_str)

            for app in reminders_hour:
                await bot.send_message(app['user_id'], f"🔔 Через час у вас запись на '{app['service']}' в {app['appointment_time']}.")
                await conn.execute('UPDATE appointments SET reminder_hour_sent = TRUE WHERE id = $1', app['id'])
        await asyncio.sleep(60)  # Проверяем каждую минуту
