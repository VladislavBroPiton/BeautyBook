import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # ID администратора в Telegram

MANAGER_IDS = list(map(int, os.getenv("MANAGER_IDS", "").split(",")))

# Настройки Google Calendar
CALENDAR_ID = os.getenv("CALENDAR_ID")
GOOGLE_CREDENTIALS_FILE = "credentials.json" # Скачаете позже
