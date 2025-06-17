# Имя файла: main.py (ФИНАЛЬНАЯ ВЕРСИЯ "ЯДЕРНЫЙ ВАРИАНТ")

import logging
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.session.httpx import HttpxSession  # <-- ГЛАВНЫЙ ИМПОРТ
from fastapi import FastAPI, Request, Response

from config import BOT_TOKEN, DATABASE_URL, REDIS_DSN
from handlers import (admin_menu_management_router, common_router, order_router,
                      report_router, staff_router, start_router)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- FastAPI приложение ---
# Мы остаемся на архитектуре "Дзен", она самая надежная
app = FastAPI(lifespan=None)


@app.post("/")
async def process_webhook(request: Request):
    """
    На каждый запрос мы будем полностью создавать и уничтожать все объекты.
    """

    # 1. Создаем сессию для бота на основе httpx
    session = HttpxSession()

    # 2. Создаем объекты бота и хранилища FSM, передавая новую сессию
    storage = RedisStorage.from_url(REDIS_DSN)
    bot = Bot(token=BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode="HTML"))

    # 3. Создаем диспетчер и регистрируем в нем роутеры
    dp = Dispatcher(storage=storage)
    dp.include_router(start_router)
    dp.include_router(common_router)
    dp.include_router(order_router)
    dp.include_router(staff_router)
    dp.include_router(admin_menu_management_router)
    dp.include_router(report_router)

    # 4. Создаем пул соединений с БД
    db_pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=60)

    # 5. Получаем обновление от Telegram
    update_data = await request.json()
    update = types.Update.model_validate(update_data, context={"bot": bot})

    try:
        # 6. Запускаем обработку, передавая пул в хендлеры
        await dp.feed_update(bot=bot, update=update, db_pool=db_pool)
    finally:
        # 7. ГАРАНТИРОВАННО ЗАКРЫВАЕМ ВСЕ СОЕДИНЕНИЯ
        await db_pool.close()
        await dp.storage.close()
        # У httpx сессии тоже есть метод close()
        await bot.session.close()
        logger.info("All connections for this request have been closed.")

    return Response(status_code=200)


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "CoffeeBotV2 is fully operational! (Httpx architecture)"}