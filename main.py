# Имя файла: main.py (ФИНАЛЬНАЯ БОЕВАЯ ВЕРСИЯ С LIFESPAN)

import logging
from contextlib import asynccontextmanager
from typing import Callable, Dict, Any, Awaitable

import asyncpg
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
# Теперь, когда мы уверены в переменных, этот способ самый правильный
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")

    # Шаг 1: Создаем пул соединений с PostgreSQL.
    db_pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=60)
    logger.info("Database connection pool established.")

    # Шаг 2: Создаем подключение к Redis для FSM.
    storage = RedisStorage.from_url(REDIS_DSN)
    logger.info("Redis storage configured.")

    # Шаг 3: Настраиваем бота и диспетчер.
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=storage)

    # Шаг 4: Регистрируем middleware и роутеры.
    dp.update.outer_middleware.register(DbPoolMiddleware(db_pool))
    dp.include_router(start_router)
    dp.include_router(common_router)
    dp.include_router(order_router)
    dp.include_router(staff_router)
    dp.include_router(admin_menu_management_router)
    dp.include_router(report_router)

    # Шаг 5: Сохраняем важные объекты в state приложения.
    app.state.bot = bot
    app.state.dp = dp

    logger.info("Dispatcher configured and ready. Application is running.")

    yield

    # Этот код выполнится при "засыпании" или остановке контейнера,
    # корректно закрывая все соединения.
    logger.info("Application shutdown...")
    await dp.storage.close()
    await bot.session.close()
    await db_pool.close()
    logger.info("Resources closed.")


app = FastAPI(lifespan=lifespan)


@app.post("/")
async def process_webhook(request: Request):
    bot: Bot = request.app.state.bot
    dp: Dispatcher = request.app.state.dp

    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot=bot, update=update)
    return Response(status_code=200)


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "CoffeeBotV2 is fully operational!"}
