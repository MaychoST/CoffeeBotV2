# Имя файла: config.py (ФИНАЛЬНАЯ БОЕВАЯ ВЕРСИЯ)
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Секреты бота
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASS")
BARISTA_PASSWORD = os.getenv("BARISTA_PASS")

# Подключения
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_DSN = os.getenv("REDIS_DSN")

# Критические проверки при запуске
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN must be set")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL must be set")
if not REDIS_DSN:
    raise ValueError("REDIS_DSN must be set")

# Некритические проверки
if not ADMIN_PASSWORD:
    logger.warning("ADMIN_PASS не установлен.")
if not BARISTA_PASSWORD:
    logger.warning("BARISTA_PASS не установлен.")