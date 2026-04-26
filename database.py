import asyncpg
from datetime import datetime

class Database:
    def __init__(self):
        self.pool = None

    async def create_pool(self, dsn: str):
        self.pool = await asyncpg.create_pool(dsn)
        await self._create_tables()
        print("Database connection pool created.")

    async def _create_tables(self):
        async with self.pool.acquire() as conn:
            # Таблица пользователей
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            # Таблица записей (appointments)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS appointments (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    service TEXT NOT NULL,
                    service_price INTEGER,
                    master TEXT,
                    master_telegram_id BIGINT,
                    appointment_date DATE NOT NULL,
                    appointment_time TIME NOT NULL,
                    client_name TEXT,
                    client_phone TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            # Добавим цену, если колонки нет
            await conn.execute('''
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='appointments' AND column_name='service_price') THEN
                        ALTER TABLE appointments ADD COLUMN service_price INTEGER;
                    END IF;
                END
                $$;
            ''')

    # ---------- Пользователи ----------
    async def add_user(self, user_id: int, username: str = None):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, username) VALUES ($1, $2)
                ON CONFLICT (user_id) DO NOTHING
            ''', user_id, username)

    # ---------- Записи ----------
    async def add_appointment(self, user_id, service, service_price, master, master_telegram_id, date, time, name, phone):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('''
                INSERT INTO appointments (user_id, service, service_price, master, master_telegram_id, appointment_date, appointment_time, client_name, client_phone)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            ''', user_id, service, service_price, master, master_telegram_id, date, time, name, phone)

    async def get_appointments_by_master_telegram_id(self, master_tg_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetch('''
                SELECT * FROM appointments
                WHERE master_telegram_id = $1 AND status = 'active'
                ORDER BY appointment_date DESC, appointment_time DESC
            ''', master_tg_id)

    async def get_appointments_by_user_id(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetch('''
                SELECT * FROM appointments
                WHERE user_id = $1 AND status = 'active'
                ORDER BY appointment_date ASC, appointment_time ASC
            ''', user_id)

    async def get_appointment_by_id(self, app_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('SELECT * FROM appointments WHERE id = $1', app_id)

    async def update_appointment(self, app_id: int, date=None, time=None, master=None, service=None):
        """Обновление записи (перенос)"""
        async with self.pool.acquire() as conn:
            if date and time:
                return await conn.execute('''
                    UPDATE appointments SET appointment_date = $1, appointment_time = $2 WHERE id = $3
                ''', date, time, app_id)
            if master:
                return await conn.execute('UPDATE appointments SET master = $1 WHERE id = $2', master, app_id)
            if service:
                return await conn.execute('UPDATE appointments SET service = $1 WHERE id = $2', service, app_id)

    async def delete_appointment(self, app_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM appointments WHERE id = $1', app_id)

    async def get_all_appointments(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch('''
                SELECT a.*, u.username FROM appointments a
                JOIN users u ON a.user_id = u.user_id
                ORDER BY a.appointment_date DESC, a.appointment_time DESC
            ''')

    # Лимит записей на мастера в день
    async def get_daily_appointments_count_for_master(self, master_tg_id: int, date: str):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT COUNT(*) FROM appointments
                WHERE master_telegram_id = $1 AND appointment_date = $2 AND status = 'active'
            ''', master_tg_id, date)
            return row[0] if row else 0

    async def check_master_limit(self, master_tg_id: int, date: str, limit: int = 5):
        count = await self.get_daily_appointments_count_for_master(master_tg_id, date)
        return count < limit
