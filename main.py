# Имя файла: main.py (ФИНАЛЬНАЯ "ОМЕГА" ВЕРСИЯ)

import logging
import asyncio
import asyncpg
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware, Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, Request, Response

from config import BOT_TOKEN, DATABASE_URL, REDIS_DSN
from handlers import (admin_menu_management_router, common_router, order_router,
                      report_router, staff_router, start_router)

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


# --- АСИНХРОННАЯ ИНИЦИАЛИЗАЦИЯ ---
# Мы создадим объекты в асинхронной функции, а потом запустим ее
async def setup_bot_objects():
    logger.info("Setting up bot objects...")

    # Проверяем наличие критически важных переменных
    if not all([BOT_TOKEN, DATABASE_URL, REDIS_DSN]):
        logger.critical("One or more critical environment variables are missing.")
        raise RuntimeError("Missing critical environment variables.")

    # 1. Создаем пул соединений с PostgreSQL
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=60)
        logger.info("Database connection pool established.")
    except Exception as e:
        logger.critical(f"Failed to create database pool: {e}", exc_info=True)
        # Если не удалось создать пул, дальнейшая работа бессмысленна
        raise

    # 2. Создаем хранилище FSM
    storage = RedisStorage.from_url(REDIS_DSN)
    logger.info("Redis storage configured.")

    # 3. Создаем объекты бота и диспетчера
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=storage)
    logger.info("Bot and Dispatcher objects created.")

    return bot, dp, db_pool


# Запускаем инициализацию и получаем готовые объекты
# Это выполнится один раз при старте контейнера Vercel
BOT_INSTANCE, DP_INSTANCE, DB_POOL_INSTANCE = asyncio.run(setup_bot_objects())


# --- MIDDLEWARE ---
# Он по-прежнему будет работать, но брать пул из глобальной переменной
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


# Регистрируем middleware
DP_INSTANCE.update.outer_middleware.register(DbPoolMiddleware(DB_POOL_INSTANCE))

# Регистрируем роутеры
DP_INSTANCE.include_router(start_router)
DP_INSTANCE.include_router(common_router)
DP_INSTANCE.include_router(order_router)
DP_INSTANCE.include_router(staff_router)
DP_INSTANCE.include_router(admin_menu_management_router)
DP_INSTANCE.include_router(report_router)
logger.info("All routers and middleware configured.")

# --- FASTAPI ПРИЛОЖЕНИЕ ---
app = FastAPI()


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Application shutdown...")
    if DB_POOL_INSTANCE:
        await DB_POOL_INSTANCE.close()
        logger.info("Database pool closed.")
    if DP_INSTANCE:
        await DP_INSTANCE.storage.close()
    if BOT_INSTANCE:
        await BOT_INSTANCE.session.close()
    logger.info("Resources closed.")


@app.post("/")
async def process_webhook(request: Request):
    update_data = await request.json()
    update = types.Update.model_validate(update_data, context={"bot": BOT_INSTANCE})
    await DP_INSTANCE.feed_update(bot=BOT_INSTANCE, update=update)
    return Response(status_code=200)


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "CoffeeBotV2 is ALIVE!"}