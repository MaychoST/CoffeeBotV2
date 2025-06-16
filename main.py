# Имя файла: main.py (ФИНАЛЬНАЯ ВЕРСИЯ 7.0 - ПРОМЫШЛЕННЫЙ СТАНДАРТ)

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

# --- ГЛОБАЛЬНЫЕ ОБЪЕКТЫ ---
# Создаем объекты здесь. Они будут существовать всегда, для любой копии приложения.
# Это решает проблему "холодных стартов".
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = RedisStorage.from_url(f"rediss://default:{REDIS_TOKEN}@{REDIS_URL.replace('https://', '')}")
dp = Dispatcher(storage=storage)


# --- MIDDLEWARE для пула соединений ---
# Это самый надежный способ передать пул в хэндлеры.
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


# --- LIFESPAN: Управляет только внешними подключениями ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")

    # Создаем и проверяем пул соединений с БД
    db_pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=60)
    await initialize_database(db_pool)
    logger.info("Database connection established and initialized.")

    # Регистрируем Middleware, передавая ему созданный пул
    dp.update.outer_middleware.register(DbPoolMiddleware(db_pool))

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
    await dp.storage.close()
    await bot.session.close()
    await db_pool.close()
    logger.info("All connections closed.")


app = FastAPI(lifespan=lifespan)


@app.post("/")
async def process_webhook(request: Request, response: Response):
    # Используем глобальные, всегда существующие объекты bot и dp
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