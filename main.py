# Имя файла: main.py (ФИНАЛЬНАЯ ВЕРСИЯ 4.0 - НАДЕЖНАЯ АРХИТЕКТУРА)

import logging
from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as redis
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, Request, Response

from config import BOT_TOKEN, DATABASE_URL, REDIS_TOKEN, REDIS_URL
from database import initialize_database
from handlers import (admin_menu_management_router, common_router, order_router,
                      report_router, staff_router, start_router)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Lifespan Manager: Создает и управляет ВСЕМИ объектами ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")

    # 1. Создаем подключения
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=60)

        redis_host_port = REDIS_URL.replace("https://", "").replace("http://", "")
        redis_connection_url = f"rediss://default:{REDIS_TOKEN}@{redis_host_port}"
        redis_client = redis.from_url(redis_connection_url, decode_responses=True)
        await redis_client.ping()

        logger.info("Database and Redis connections established.")
    except Exception as e:
        logger.critical(f"Failed to establish connections: {e}", exc_info=True)
        raise

    # 2. Инициализируем БД
    await initialize_database(db_pool)
    logger.info("Database initialized.")

    # 3. Создаем и конфигурируем Aiogram ПОСЛЕ всех подключений
    storage = RedisStorage(redis=redis_client)
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

    # Инициализируем Dispatcher СРАЗУ с хранилищем и пулом БД
    dp = Dispatcher(storage=storage, db_pool=db_pool)

    # Включаем все роутеры
    dp.include_router(start_router)
    dp.include_router(common_router)
    dp.include_router(order_router)
    dp.include_router(staff_router)
    dp.include_router(admin_menu_management_router)
    dp.include_router(report_router)

    # 4. Сохраняем готовые объекты в state приложения
    app.state.bot = bot
    app.state.dp = dp

    logger.info("Dispatcher configured and dependencies stored in app.state.")

    yield

    logger.info("Application shutdown...")
    if app.state.dp:
        await app.state.dp.storage.close()
    if app.state.bot:
        await app.state.bot.session.close()
    # Пул больше не хранится в app.state, он внутри dp, но закроем его явно, если он был создан
    if 'db_pool' in locals() and db_pool:
        await db_pool.close()
        logger.info("Database pool closed.")
    logger.info("Resources closed.")


app = FastAPI(lifespan=lifespan)


@app.post("/")
async def process_webhook(request: Request, response: Response):
    # Берем объекты из app.state - это самый надежный способ в FastAPI
    bot: Bot = request.app.state.bot
    dp: Dispatcher = request.app.state.dp

    try:
        update_data = await request.json()
        update = types.Update.model_validate(update_data, context={"bot": bot})
        await dp.feed_update(bot=bot, update=update)
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        response.status_code = 200
        return response

    response.status_code = 200
    return response


@app.get("/")
async def health_check():
    return {"status": "ok"}