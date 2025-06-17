# Имя файла: config.py (ФИНАЛЬНАЯ ВЕРСИЯ С REDIS_DSN)
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
# Пример: postgresql://user:password@host:port/dbname
DATABASE_URL = os.getenv("DATABASE_URL")

# ИЗМЕНЕНИЕ: Используем единую строку подключения (DSN) для Redis
# Пример: rediss://default:password@host:port
REDIS_DSN = os.getenv("REDIS_DSN")


# --- Критические проверки при запуске ---
if not BOT_TOKEN:
    logger.critical("Критическая ошибка: Переменная окружения TELEGRAM_BOT_TOKEN не установлена!")
    raise ValueError("TELEGRAM_BOT_TOKEN must be set")

if not DATABASE_URL:
    logger.critical("Критическая ошибка: Переменная окружения DATABASE_URL не установлена!")
    raise ValueError("DATABASE_URL must be set")

# ИЗМЕНЕНИЕ: Проверяем только одну переменную REDIS_DSN
if not REDIS_DSN:
    logger.critical("Критическая ошибка: Переменная окружения REDIS_DSN не установлена!")
    raise ValueError("REDIS_DSN must be set")

# --- Некритические проверки (предупреждения) ---
if not ADMIN_PASSWORD:
    logger.warning("Переменная окружения ADMIN_PASS не установлена. Функционал администратора будет недоступен.")

if not BARISTA_PASSWORD:
    logger.warning("Переменная окружения BARISTA_PASS не установлена. Функционал бариста будет недоступен.")