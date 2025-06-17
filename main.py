# Имя файла: main.py (ФИНАЛЬНАЯ ВЕРСИЯ - ИСПРАВЛЕНИЕ ОШИБКИ РОУТЕРОВ)

import logging
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.session.aiohttp import AiohttpSession
from fastapi import FastAPI, Request, Response

from config import BOT_TOKEN, DATABASE_URL, REDIS_DSN

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


# --- ФУНКЦИЯ ДЛЯ СБОРКИ ДИСПЕТЧЕРА ---
# Мы вынесли это в отдельную функцию, чтобы не загромождать webhook
def setup_dispatcher(storage: RedisStorage) -> Dispatcher:
    dp = Dispatcher(storage=storage)

    # Импортируем роутеры здесь, чтобы они были "свежими"
    from handlers.common_handler import router as common_router
    from handlers.order_handler import router as order_router
    from handlers.staff_handler import router as staff_router
    from handlers.admin_menu_management_handler import router as admin_menu_management_router
    from handlers.report_handler import router as report_router
    from handlers.start_handler import router as start_router

    # ПРАВИЛЬНЫЙ ПОРЯДОК РЕГИСТРАЦИИ
    dp.include_router(common_router)
    dp.include_router(order_router)
    dp.include_router(staff_router)
    dp.include_router(admin_menu_management_router)
    dp.include_router(report_router)
    # Роутер с обработкой простого текста СТАВИМ В САМЫЙ КОНЕЦ
    dp.include_router(start_router)

    return dp


# --- FastAPI приложение ---
app = FastAPI(lifespan=None)


@app.post("/")
async def process_webhook(request: Request):
    """
    На каждый запрос мы будем полностью создавать и уничтожать все объекты.
    """

    session = AiohttpSession()
    storage = RedisStorage.from_url(REDIS_DSN)
    bot = Bot(token=BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode="HTML"))

    # Создаем и настраиваем диспетчер
    dp = setup_dispatcher(storage)

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
    return {"status": "ok", "message": "CoffeeBotV2 is fully operational! (Router fix)"}
