# Имя файла: config.py (ДИАГНОСТИЧЕСКАЯ ВЕРСИЯ БЕЗ ПРОВЕРОК)
import os
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

logger = logging.getLogger(__name__)

# --- Секреты бота ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASS")
BARISTA_PASSWORD = os.getenv("BARISTA_PASS")

# --- Переменные для подключения к базам данных ---
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_DSN = os.getenv("REDIS_DSN")


# --- ПРОВЕРКИ (ОСТАВЛЯЕМ ТОЛЬКО ЛОГИРОВАНИЕ ДЛЯ ДИАГНОСТИКИ) ---
if not BOT_TOKEN:
    logger.critical("ДИАГНОСТИКА: Переменная окружения TELEGRAM_BOT_TOKEN не найдена!")
    # raise ValueError("TELEGRAM_BOT_TOKEN must be set")

if not DATABASE_URL:
    logger.critical("ДИАГНОСТИКА: Переменная окружения DATABASE_URL не найдена!")
    # raise ValueError("DATABASE_URL must be set")

if not REDIS_DSN:
    logger.critical("ДИАГНОСТИКА: Переменная окружения REDIS_DSN не найдена!")
    # raise ValueError("REDIS_DSN must be set")

# --- Некритические проверки (предупреждения) ---
if not ADMIN_PASSWORD:
    logger.warning("Переменная окружения ADMIN_PASS не установлена. Функционал администратора будет недоступен.")

if not BARISTA_PASSWORD:
    logger.warning("Переменная окружения BARISTA_PASS не установлена. Функционал бариста будет недоступен.")