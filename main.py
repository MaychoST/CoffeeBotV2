import asyncio
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
    ADMIN_PASSWORD,  # <--- ИСПРАВЛЕНО
    BARISTA_PASSWORD,  # <--- ИСПРАВЛЕНО
)
from database import init_db
from handlers import (
    admin_menu_management_router,
    common_router,
    order_router,
    report_router,
    staff_router,
    start_router,
)

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Lifespan Manager: Управляет ресурсами (БД, Redis) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")
    # Создаем подключения
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=60)
        upstash_redis_url = f"rediss://default:{REDIS_TOKEN}@{REDIS_URL.replace('https://', '')}"
        redis_client = redis.from_url(upstash_redis_url, decode_responses=True)
        await redis_client.ping()  # Проверяем соединение
        logger.info("Database and Redis connections established.")
    except Exception as e:
        logger.critical(f"Failed to establish connections: {e}")
        raise

    # Инициализируем БД
    await init_db(db_pool)
    logger.info("Database initialized.")

    # Создаем и настраиваем Aiogram
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    storage = RedisStorage(redis=redis_client)
    dp = Dispatcher(storage=storage)

    # Регистрируем роутеры
    dp.include_router(start_router)
    dp.include_router(common_router)
    dp.include_router(order_router)
    dp.include_router(admin_menu_management_router)
    dp.include_router(staff_router)
    dp.include_router(report_router)

    # Сохраняем объекты в состояние приложения, чтобы иметь к ним доступ
    app.state.bot = bot
    app.state.dp = dp
    app.state.db_pool = db_pool

    yield

    # Закрываем подключения при остановке
    logger.info("Application shutdown...")
    await app.state.dp.storage.close()
    await app.state.bot.session.close()
    await app.state.db_pool.close()
    logger.info("Resources closed.")


# --- Создание приложения FastAPI с управлением жизненным циклом ---
app = FastAPI(lifespan=lifespan)


# --- Вебхук-обработчик ---
@app.post("/")
async def process_webhook(request: Request):
    # Берем объекты bot и dp из состояния приложения
    bot: Bot = request.app.state.bot
    dp: Dispatcher = request.app.state.dp

    # Передаем обновление в Aiogram
    update_data = await request.json()
    update = types.Update.model_validate(update_data, context={"bot": bot})
    await dp.feed_update(bot=bot, update=update)

    return Response(status_code=200)


@app.get("/")
async def health_check():
    return {"status": "ok"}
