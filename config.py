# config.py
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

# ### ИЗМЕНЕНИЕ: Добавили переменные для подключения к PostgreSQL и Redis ###
# Пример: postgresql://user:password@host:port/dbname
DATABASE_URL = os.getenv("DATABASE_URL")

# Пример: redis://localhost:6379/0
REDIS_URL = os.getenv("REDIS_URL")
REDIS_TOKEN = os.getenv("REDIS_TOKEN")

# --- Критические проверки при запуске ---
if not BOT_TOKEN:
    logger.critical("Критическая ошибка: Переменная окружения TELEGRAM_BOT_TOKEN не установлена!")
    raise ValueError("TELEGRAM_BOT_TOKEN must be set")

if not DATABASE_URL:
    logger.critical("Критическая ошибка: Переменная окружения DATABASE_URL не установлена!")
    raise ValueError("DATABASE_URL must be set")

if not REDIS_URL:
    logger.critical("Критическая ошибка: Переменная окружения REDIS_URL не установлена!")
    raise ValueError("REDIS_URL must be set")
if not REDIS_TOKEN:  # <--- ДОБАВИТЬ ЭТОТ БЛОК
    logger.critical("Критическая ошибка: Переменная окружения REDIS_TOKEN не установлена!")
    raise ValueError("REDIS_TOKEN must be set")

# --- Некритические проверки (предупреждения) ---
if not ADMIN_PASSWORD:
    logger.warning("Переменная окружения ADMIN_PASS не установлена. Функционал администратора будет недоступен.")

if not BARISTA_PASSWORD:
    logger.warning("Переменная окружения BARISTA_PASS не установлена. Функционал бариста будет недоступен.")
