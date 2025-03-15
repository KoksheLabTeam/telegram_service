import os
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные из .env

DB_URL = os.getenv("DB_URL")
DB_ECHO = False
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID")