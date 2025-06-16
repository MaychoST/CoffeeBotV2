# Имя файла: main.py (ФИНАЛЬНАЯ ВЕРСИЯ 9.0 - С nest_asyncio)
import asyncio

# <<< ГЛАВНОЕ ИЗМЕНЕНИЕ: Устраняем конфликт циклов событий >>>
import nest_asyncio

nest_asyncio.apply()
# <<< КОНЕЦ ИЗМЕНЕНИЯ >>>

import logging
from contextlib import asynccontextmanager
from typing import Callable, Dict, Any, Awaitable

import asyncpg
import redis.asyncio as redis
from aiogram import BaseMiddleware, Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, Request, Response

from config import BOT_TOKEN, DATABASE_URL, REDIS_TOKEN, REDIS_URL
from database import initialize_database
from handlers import (admin_menu_management_router, common_router, order_router,
                      report_router, staff_router, start_router)

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


# --- MIDDLEWARE для пула соединений ---
class DbPoolMiddleware(BaseMiddleware):
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def __call__(
            self,
            handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: types.TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        data["db_pool"] = self.pool
        return await handler(event, data)


# --- LIFESPAN: Управляет только подключениями ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")

    # --- Создаем глобальные переменные внутри lifespan ---
    # Это гарантирует, что они создаются в правильном цикле событий.
    app.state.db_pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=60)
    await initialize_database(app.state.db_pool)
    logger.info("Database connection established and initialized.")

    redis_connection_url = f"rediss://default:{REDIS_TOKEN}@{REDIS_URL.replace('https://', '').replace('http://', '')}"
    storage = RedisStorage.from_url(redis_connection_url)

    app.state.bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    app.state.dp = Dispatcher(storage=storage)

    # Включаем все роутеры
    app.state.dp.include_router(start_router)
    app.state.dp.include_router(common_router)
    app.state.dp.include_router(order_router)
    app.state.dp.include_router(staff_router)
    app.state.dp.include_router(admin_menu_management_router)
    app.state.dp.include_router(report_router)

    # Регистрируем Middleware
    app.state.dp.update.outer_middleware.register(DbPoolMiddleware(app.state.db_pool))

    logger.info("Dispatcher configured.")

    yield

    logger.info("Application shutdown...")
    if hasattr(app.state, 'dp') and app.state.dp:
        await app.state.dp.storage.close()
    if hasattr(app.state, 'bot') and app.state.bot:
        await app.state.bot.session.close()
    if hasattr(app.state, 'db_pool') and app.state.db_pool:
        await app.state.db_pool.close()
        logger.info("Database pool closed.")
    logger.info("Resources closed.")


app = FastAPI(lifespan=lifespan)


@app.post("/")
async def process_webhook(request: Request, response: Response):
    try:
        update_data = await request.json()
        update = types.Update.model_validate(update_data, context={"bot": request.app.state.bot})
        await request.app.state.dp.feed_update(bot=request.app.state.bot, update=update)
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        response.status_code = 200
        return response

    response.status_code = 200
    return response


@app.get("/")
async def health_check():
    return {"status": "ok"}