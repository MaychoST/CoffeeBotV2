# Имя файла: main.py (ФИНАЛЬНАЯ ВЕРСИЯ 2.2 - ИСПРАВЛЕНА ОШИБКА STATE)

import logging
from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as redis
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, Request, Response

from config import (
    BOT_TOKEN,
    DATABASE_URL,
    REDIS_TOKEN,
    REDIS_URL,
)
from database import initialize_database
from handlers import (
    admin_menu_management_router,
    common_router,
    order_router,
    report_router,
    staff_router,
    start_router,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")

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

    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    storage = RedisStorage(redis=redis_client)
    dp = Dispatcher(storage=storage, db_pool=db_pool)

    dp.include_router(start_router)
    dp.include_router(common_router)
    dp.include_router(order_router)
    dp.include_router(staff_router)
    dp.include_router(admin_menu_management_router)
    dp.include_router(report_router)

    # <<< ВОТ ОНО, ИСПРАВЛЕНИЕ! ВОЗВРАЩАЕМ СОХРАНЕНИЕ В STATE >>>
    app.state.bot = bot
    app.state.dp = dp

    yield

    logger.info("Application shutdown...")
    await dp.storage.close()
    await bot.session.close()

    pool_to_close = dp.workflow_data.get('db_pool')
    if pool_to_close:
        await pool_to_close.close()
        logger.info("Database pool closed.")
    logger.info("Resources closed.")


app = FastAPI(lifespan=lifespan)


@app.post("/")
async def process_webhook(request: Request, response: Response):
    # Теперь этот код будет работать, потому что bot и dp есть в app.state
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