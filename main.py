# Имя файла: main.py (ФИНАЛЬНАЯ ВЕРСИЯ)

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
# <<< ИЗМЕНЕНИЕ: Импортируем новую функцию
from database import initialize_database
# <<< ИЗМЕНЕНИЕ: Импорты теперь должны работать благодаря новому __init__.py
from handlers import (
    # admin_menu_management_router,
    common_router,
    order_router,
    # report_router,
    # staff_router,
    start_router,
)

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Lifespan Manager: Управляет ресурсами (БД, Redis) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")
    # Создаем подключения
    try:
        # <<< ИЗМЕНЕНИЕ: Создаем пул соединений PostgreSQL
        db_pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=60)

        # <<< ИЗМЕНЕНИЕ: Формируем URL для Upstash Redis
        # Формат: rediss://default:<password>@<host>:<port>
        upstash_redis_url = f"rediss://default:{REDIS_TOKEN}@{REDIS_URL.split('//')[1]}"
        redis_client = redis.from_url(upstash_redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info("Database and Redis connections established.")
    except Exception as e:
        logger.critical(f"Failed to establish connections: {e}", exc_info=True)
        raise

    # <<< КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Инициализируем БД, передавая пул
    await initialize_database(db_pool)
    logger.info("Database initialized.")

    # Создаем и настраиваем Aiogram
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    storage = RedisStorage(redis=redis_client)

    # <<< КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Передаем пул соединений в Dispatcher.
    # Теперь он будет доступен во всех хэндлерах через `state.bot.db_pool` или как аргумент.
    # Для этого мы передаем его как keyword-аргумент.
    dp = Dispatcher(storage=storage, db_pool=db_pool)

    # Регистрируем роутеры
    dp.include_router(start_router)
    dp.include_router(common_router)
    dp.include_router(order_router)
    # dp.include_router(admin_menu_management_router) # <-- Временно отключен
    # dp.include_router(staff_router) # <-- Временно отключен
    # dp.include_router(report_handler) # <-- Временно отключен

    # Сохраняем объекты в состояние приложения, чтобы иметь к ним доступ в вебхуке
    app.state.bot = bot
    app.state.dp = dp

    # Пул больше не нужно хранить в app.state, так как он теперь внутри Dispatcher
    # app.state.db_pool = db_pool

    yield

    # Закрываем подключения при остановке
    logger.info("Application shutdown...")
    await dp.storage.close()
    await dp.fsm.storage.close()  # Явное закрытие для некоторых версий
    await bot.session.close()

    # <<< ИЗМЕНЕНИЕ: Получаем пул из диспетчера для закрытия
    pool_to_close = dp.workflow_data.get('db_pool')
    if pool_to_close:
        await pool_to_close.close()
        logger.info("Database pool closed.")
    logger.info("Resources closed.")


# --- Создание приложения FastAPI с управлением жизненным циклом ---
app = FastAPI(lifespan=lifespan)


# --- Вебхук-обработчик ---
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
        # Важно вернуть 200, чтобы телеграм не пытался повторить отправку
        response.status_code = 200
        return response

    response.status_code = 200
    return response


@app.get("/")
async def health_check():
    return {"status": "ok"}
