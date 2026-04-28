import asyncpg
import logging
from datetime import date, time, datetime
from typing import Optional

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool = None

    async def create_pool(self, dsn: str):
        self.pool = await asyncpg.create_pool(dsn)
        logger.info("Database pool created")

    async def add_user(self, user_id: int, username: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id, username) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET username=$2",
                user_id, username
            )

    async def add_appointment(self, user_id: int, service: str, service_price: int,
                              master: str, master_telegram_id: int,
                              date: str, time: str, name: str, phone: str):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO appointments 
                (user_id, service, service_price, master, master_telegram_id,
                 appointment_date, appointment_time, client_name, client_phone)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING id""",
                user_id, service, service_price, master, master_telegram_id,
                date, time, name, phone
            )
            return row['id']

    async def get_appointments_by_user_id(self, user_id: int):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM appointments WHERE user_id=$1 AND appointment_date >= CURRENT_DATE ORDER BY appointment_date, appointment_time",
                user_id
            )
            return [dict(r) for r in rows]

    async def get_appointments_by_master_telegram_id(self, master_telegram_id: int):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM appointments
                   WHERE master_telegram_id = $1
                     AND (appointment_date > CURRENT_DATE
                          OR (appointment_date = CURRENT_DATE AND appointment_time > CURRENT_TIME))
                   ORDER BY appointment_date, appointment_time""",
                master_telegram_id
            )
            return [dict(r) for r in rows]

    async def get_appointment_by_id(self, appointment_id: int):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM appointments WHERE id=$1", appointment_id)
            return dict(row) if row else None

    async def delete_appointment(self, appointment_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM appointments WHERE id=$1", appointment_id)

    async def get_all_appointments(self):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT a.*, u.username FROM appointments a JOIN users u ON a.user_id = u.user_id ORDER BY appointment_date, appointment_time"
            )
            return [dict(r) for r in rows]

    async def check_master_limit(self, master_telegram_id: int, date_str: str, limit: int):
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM appointments WHERE master_telegram_id=$1 AND appointment_date=$2",
                master_telegram_id, date_str
            )
            return count < limit

    async def is_slot_available(self, master_telegram_id: int, date_str: str, time_str: str):
        async with self.pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM appointments WHERE master_telegram_id=$1 AND appointment_date=$2 AND appointment_time=$3)",
                master_telegram_id, date_str, time_str
            )
            return not exists

    async def get_busy_slots_for_master(self, master_telegram_id: int, date_str: str):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT appointment_time FROM appointments WHERE master_telegram_id=$1 AND appointment_date=$2",
                master_telegram_id, date_str
            )
            return [r['appointment_time'].strftime("%H:%M") if isinstance(r['appointment_time'], time) else str(r['appointment_time']) for r in rows]

    async def get_appointments_for_reminder(self, target_date: str, reminder_type: str, target_time: Optional[str] = None):
        async with self.pool.acquire() as conn:
            if reminder_type == 'day':
                query = """SELECT a.*, u.user_id FROM appointments a JOIN users u ON a.user_id = u.user_id
                           WHERE a.appointment_date = $1 AND (a.reminder_day_sent IS NOT TRUE)"""
                rows = await conn.fetch(query, target_date)
            elif reminder_type == 'hour':
                query = """SELECT a.*, u.user_id FROM appointments a JOIN users u ON a.user_id = u.user_id
                           WHERE a.appointment_date = $1 AND a.appointment_time = $2 AND (a.reminder_hour_sent IS NOT TRUE)"""
                rows = await conn.fetch(query, target_date, target_time)
            else:
                return []
            return [dict(r) for r in rows]

    async def mark_reminder_sent(self, appointment_id: int, reminder_type: str):
        async with self.pool.acquire() as conn:
            if reminder_type == 'day':
                await conn.execute("UPDATE appointments SET reminder_day_sent = TRUE WHERE id=$1", appointment_id)
            elif reminder_type == 'hour':
                await conn.execute("UPDATE appointments SET reminder_hour_sent = TRUE WHERE id=$1", appointment_id)

    async def get_appointments_count(self):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM appointments")

    async def get_appointments_count_for_date(self, d: date):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM appointments WHERE appointment_date=$1", d)

    async def get_appointments_grouped_by_service(self):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT service, COUNT(*) as count FROM appointments GROUP BY service")
            return [dict(r) for r in rows]

    async def get_appointments_grouped_by_master(self):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT master, COUNT(*) as count FROM appointments GROUP BY master")
            return [dict(r) for r in rows]
