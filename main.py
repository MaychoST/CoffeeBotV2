# Имя файла: main.py (ФИНАЛЬНАЯ ВЕРСИЯ - КЛОНИРОВАНИЕ РОУТЕРОВ)

import logging
import asyncpg
from copy import deepcopy
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.session.aiohttp import AiohttpSession
from fastapi import FastAPI, Request, Response

from config import BOT_TOKEN, DATABASE_URL, REDIS_DSN
# Возвращаем глобальные импорты, но будем их клонировать
from handlers import (common_router, order_router, staff_router,
                      admin_menu_management_router, report_router, start_router)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Список наших роутеров ---
# Мы определим их один раз, чтобы было удобно
ALL_ROUTERS = [
    common_router,
    order_router,
    staff_router,
    admin_menu_management_router,
    report_router,
    start_router,  # <-- Порядок здесь важен
]

# --- FastAPI приложение ---
app = FastAPI(lifespan=None)


@app.post("/")
async def process_webhook(request: Request):
    """
    Создаем все объекты на каждый запрос, чтобы избежать проблем с состоянием.
    """

    session = AiohttpSession()
    storage = RedisStorage.from_url(REDIS_DSN)
    bot = Bot(token=BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=storage)

    # КЛОНИРУЕМ И РЕГИСТРИРУЕМ РОУТЕРЫ
    # deepcopy создает полную, независимую копию каждого роутера
    for router_obj in ALL_ROUTERS:
        dp.include_router(deepcopy(router_obj))

    # Создаем пул соединений с БД
    db_pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=60)

    # Получаем и обрабатываем обновление
    update_data = await request.json()
    update = types.Update.model_validate(update_data, context={"bot": bot})

    try:
        await dp.feed_update(bot=bot, update=update, db_pool=db_pool)
    finally:
        # Закрываем все соединения
        await db_pool.close()
        await dp.storage.close()
        await bot.session.close()

    return Response(status_code=200)


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "CoffeeBotV2 is fully operational! (Cloned Routers)"}