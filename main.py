# Имя файла: main.py (ФИНАЛЬНАЯ ВЕРСИЯ С REDIS_DSN)

import logging
from contextlib import asynccontextmanager
from typing import Callable, Dict, Any, Awaitable

import asyncpg
from aiogram import BaseMiddleware, Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, Request, Response

from config import BOT_TOKEN, DATABASE_URL, REDIS_DSN  # <-- ИЗМЕНЕНИЕ ЗДЕСЬ
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


# --- LIFESPAN: Управляет жизненным циклом приложения ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")

    # Шаг 1: Создаем пул соединений с PostgreSQL.
    db_pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=60)
    logger.info("Database connection pool established.")

    # Шаг 2: Создаем подключение к Redis для FSM, используя готовую строку DSN
    # <-- ГЛАВНОЕ ИЗМЕНЕНИЕ ЗДЕСЬ
    storage = RedisStorage.from_url(REDIS_DSN)
    logger.info("Redis storage configured.")

    # Шаг 3: Настраиваем бота и диспетчер
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=storage)

    dp.include_router(start_router)
    dp.include_router(common_router)
    dp.include_router(order_router)
    dp.include_router(staff_router)
    dp.include_router(admin_menu_management_router)
    dp.include_router(report_router)

    dp.update.outer_middleware.register(DbPoolMiddleware(db_pool))

    # Шаг 4: Сохраняем важные объекты в state приложения для доступа из обработчиков
    app.state.bot = bot
    app.state.dp = dp
    app.state.db_pool = db_pool

    logger.info("Dispatcher configured and ready. Application is running.")

    yield

    # --- Код, который выполнится при остановке приложения ---
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
    bot: Bot = request.app.state.bot
    dp: Dispatcher = request.app.state.dp

    try:
        update_data = await request.json()
        update = types.Update.model_validate(update_data, context={"bot": bot})
        await dp.feed_update(bot=bot, update=update)
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        # В боевом режиме всегда возвращаем 200, чтобы Telegram не спамил
        response.status_code = 200
        return response

    response.status_code = 200
    return response


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "CoffeeBotV2 is alive!"}
