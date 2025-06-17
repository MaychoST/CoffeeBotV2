# Имя файла: init_db.py (УПРОЩЕННАЯ ВЕРСИЯ)

import asyncio
import logging
import os
import asyncpg
from dotenv import load_dotenv
from database import initialize_database

# Настройка логирования, чтобы видеть, что происходит
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Загружаем переменные прямо здесь
load_dotenv()


async def main():
    """
    Основная функция для подключения к БД и ее инициализации.
    """
    # Получаем DATABASE_URL напрямую из окружения
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        logger.critical("Переменная окружения DATABASE_URL не найдена в .env файле!")
        return

    logger.info("Подключение к базе данных...")
    pool = None
    try:
        # Устанавливаем соединение с базой данных
        pool = await asyncpg.create_pool(database_url, command_timeout=60)
        logger.info("Пул соединений создан.")

        # Выполняем инициализацию (создание и заполнение таблиц)
        await initialize_database(pool)

        logger.info("ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ УСПЕШНО ЗАВЕРШЕНА!")

    except Exception as e:
        logger.critical(f"Произошла критическая ошибка при инициализации БД: {e}", exc_info=True)
    finally:
        if pool:
            await pool.close()
            logger.info("Пул соединений закрыт.")


if __name__ == "__main__":
    # Убедитесь, что у вас есть файл .env с DATABASE_URL
    asyncio.run(main())
