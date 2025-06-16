# main.py
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as redis
from aiogram.types import Update, BotCommand
from fastapi import FastAPI

from config import BOT_TOKEN, DATABASE_URL, REDIS_URL, REDIS_TOKEN
from handlers import (
    start_handler,
    order_handler,
    staff_handler,
    admin_menu_management_handler,
    report_handler,
    common_handler  # Оставляем импорт, но изменим порядок
)
from database import get_db_pool, close_db_pool, create_tables, _check_and_populate

# --- Настройка ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Создаем клиент Redis с указанием токена
redis_client = redis.from_url(REDIS_URL, password=REDIS_TOKEN, decode_responses=True)

# Передаем готовый клиент в хранилище
storage = RedisStorage(redis=redis_client)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

# --- ВОЗВРАЩАЕМ СТАРЫЙ, РАБОЧИЙ ПОРЯДОК РОУТЕРОВ ---
dp.include_router(admin_menu_management_handler.router)
dp.include_router(report_handler.router)
dp.include_router(order_handler.router)
dp.include_router(staff_handler.router)
# ВАЖНО: common_handler и start_handler должны быть в конце
dp.include_router(common_handler.router)
dp.include_router(start_handler.router)


async def set_main_menu(bot: Bot):
    # Эта функция остается, она не ломает ничего
    main_menu_commands = [
        BotCommand(command="/start", description="Перезагрузить / Авторизация ⚙️"),
        BotCommand(command="/logout", description="Выйти из системы 🚪"),
        BotCommand(command="/help", description="Помощь по боту ❓"),
        BotCommand(command="/bug", description="Сообщить об ошибке 🐞")
    ]
    await bot.set_my_commands(main_menu_commands)
    logger.info("Основные команды меню установлены.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Приложение запускается, инициализируем ресурсы...")
    await set_main_menu(bot)
    await get_db_pool()
    await create_tables()
    await _check_and_populate()
    logger.info("База данных и ресурсы инициализированы.")
    yield
    logger.info("Приложение останавливается, освобождаем ресурсы...")
    await close_db_pool()
    await bot.session.close()
    await dp.storage.close()
    logger.info("Все ресурсы успешно освобождены.")


app = FastAPI(lifespan=lifespan)


@app.post("/")
async def process_webhook(update: Update):
    await dp.feed_update(bot=bot, update=update)
    return {'status': 'ok'}
