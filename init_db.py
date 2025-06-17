# Имя файла: init_db.py

import asyncio
import logging
import asyncpg
from config import DATABASE_URL
from database import initialize_database

# Настройка логирования, чтобы видеть, что происходит
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    """
    Основная функция для подключения к БД и ее инициализации.
    """
    if not DATABASE_URL:
        logger.critical("Переменная окружения DATABASE_URL не установлена!")
        return

    logger.info("Подключение к базе данных...")
    pool = None
    try:
        # Устанавливаем соединение с базой данных
        pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=60)
        logger.info("Пул соединений создан.")

        # Выполняем инициализацию (создание и заполнение таблиц)
        await initialize_database(pool)

        logger.info("Инициализация базы данных успешно завершена!")

    except Exception as e:
        logger.critical(f"Произошла критическая ошибка при инициализации БД: {e}", exc_info=True)
    finally:
        if pool:
            await pool.close()
            logger.info("Пул соединений закрыт.")


if __name__ == "__main__":
    # Убедитесь, что у вас есть файл .env с DATABASE_URL
    # и выполните `pip install -r requirements.txt` перед запуском
    asyncio.run(main())
