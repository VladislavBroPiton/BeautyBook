import asyncpg
from datetime import datetime

class Database:
    def __init__(self):
        self.pool = None

    async def create_pool(self, dsn: str):
        """Создание пула подключений к базе данных."""
        self.pool = await asyncpg.create_pool(dsn)
        await self._create_tables()
        print("Database connection pool created.")

    async def _create_tables(self):
        """Создание таблиц, если они не существуют."""
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
                    master TEXT,
                    appointment_date DATE NOT NULL,
                    appointment_time TIME NOT NULL,
                    client_name TEXT,
                    client_phone TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')

    # --- Методы для работы с пользователями ---
    async def add_user(self, user_id: int, username: str = None):
        """Добавляет нового пользователя, если его нет."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, username) VALUES ($1, $2)
                ON CONFLICT (user_id) DO NOTHING
            ''', user_id, username)

    # --- Методы для работы с записями ---
    async def add_appointment(self, user_id, service, master, date, time, name, phone):
        """Добавляет новую запись в БД."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('''
                INSERT INTO appointments (user_id, service, master, appointment_date, appointment_time, client_name, client_phone)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            ''', user_id, service, master, date, time, name, phone)

    async def get_appointments_for_date(self, date: str, master: str):
        """Возвращает список занятых слотов на определенную дату для мастера."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT appointment_time FROM appointments 
                WHERE appointment_date = $1 AND master = $2
            ''', date, master)
            return [row['appointment_time'].strftime("%H:%M") for row in rows]

    async def get_all_appointments(self):
        """Возвращает все записи (для администратора)."""
        async with self.pool.acquire() as conn:
            return await conn.fetch('''
                SELECT a.*, u.username FROM appointments a
                JOIN users u ON a.user_id = u.user_id
                ORDER BY a.appointment_date DESC, a.appointment_time DESC
            ''')
