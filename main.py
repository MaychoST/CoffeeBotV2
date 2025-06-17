# Имя файла: main.py (САМАЯ ФИНАЛЬНАЯ ВЕРСИЯ)

import logging
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, Request, Response

from config import BOT_TOKEN, DATABASE_URL, REDIS_DSN
from handlers import (admin_menu_management_router, common_router, order_router,
                      report_router, staff_router, start_router)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Создаем "дешевые" объекты глобально
storage = RedisStorage.from_url(REDIS_DSN)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=storage)

# Регистрируем роутеры
dp.include_router(start_router)
dp.include_router(common_router)
dp.include_router(order_router)
dp.include_router(staff_router)
dp.include_router(admin_menu_management_router)
dp.include_router(report_router)
logger.info("Bot, Dispatcher, and Routers are configured.")

# FastAPI приложение
app = FastAPI()


@app.post("/")
async def process_webhook(request: Request):
    # Создаем пул на каждый запрос
    pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=60)

    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    try:
        # Передаем пул напрямую в хендлеры!
        # Aiogram автоматически подставит его в те хендлеры, где он указан как аргумент `db_pool: asyncpg.Pool`
        await dp.feed_update(bot=bot, update=update, db_pool=pool)
    finally:
        # Гарантированно закрываем пул
        await pool.close()

    return Response(status_code=200)


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "CoffeeBotV2 is fully operational!"}