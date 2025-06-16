# Имя файла: main.py (ФИНАЛЬНАЯ ВЕРСИЯ 5.0 - УСТОЙЧИВАЯ К ХОЛОДНЫМ СТАРТАМ)

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

# --- ГЛАВНОЕ ИЗМЕНЕНИЕ: Создаем объекты здесь, в глобальной области ---
# Они будут созданы один раз при первой загрузке модуля Python.
db_pool: asyncpg.Pool | None = None
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage: RedisStorage | None = None
dp = Dispatcher()  # Пока пустой, настроим в lifespan


# --- Lifespan Manager: Управляет только подключениями и конфигурацией ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, storage, dp
    logger.info("Application startup: establishing connections...")

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

    await initialize_database(db_pool)
    logger.info("Database initialized.")

    storage = RedisStorage(redis=redis_client)
    dp.storage = storage
    dp.workflow_data["db_pool"] = db_pool

    # Включаем все роутеры
    dp.include_router(start_router)
    dp.include_router(common_router)
    dp.include_router(order_router)
    dp.include_router(staff_router)
    dp.include_router(admin_menu_management_router)
    dp.include_router(report_router)

    logger.info("Dispatcher configured.")

    yield

    logger.info("Application shutdown...")
    if dp and dp.storage:
        await dp.storage.close()
    if bot and bot.session:
        await bot.session.close()
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed.")
    logger.info("Resources closed.")


app = FastAPI(lifespan=lifespan)


@app.post("/")
async def process_webhook(request: Request, response: Response):
    # --- ИЗМЕНЕНИЕ: Берем объекты из глобальной области, а не из app.state ---
    global bot, dp

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