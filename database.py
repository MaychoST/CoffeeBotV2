# Имя файла: database.py (ФИНАЛЬНАЯ ВЕРСИЯ)

import asyncpg
import logging
from datetime import date
from typing import List, Optional, Any, Tuple

from menu_data import MENU

logger = logging.getLogger(__name__)


async def _execute(pool: asyncpg.Pool, query: str, *params, fetch: Optional[str] = None) -> Any:
    async with pool.acquire() as connection:
        try:
            if fetch == 'val':
                return await connection.fetchval(query, *params)
            elif fetch == 'row':
                return await connection.fetchrow(query, *params)
            elif fetch == 'all':
                return await connection.fetch(query, *params)
            else:
                return await connection.execute(query, *params)
        except asyncpg.PostgresError as e:
            logger.error(f"Ошибка выполнения запроса в PostgreSQL: {e}\nЗапрос: {query}\nПараметры: {params}",
                         exc_info=True)
            if fetch in ['val', 'row']: return None
            if fetch == 'all': return []
            return None


async def create_tables(pool: asyncpg.Pool):
    queries = [
        # ... (здесь все ваши CREATE TABLE запросы, без изменений) ...
        """CREATE TABLE IF NOT EXISTS menu_categories (id SERIAL PRIMARY KEY, name TEXT NOT NULL, is_active BOOLEAN DEFAULT TRUE, sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS menu_items (id SERIAL PRIMARY KEY, category_id INTEGER NOT NULL REFERENCES menu_categories(id) ON DELETE CASCADE, name TEXT NOT NULL, description TEXT, is_active BOOLEAN DEFAULT TRUE, sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS menu_item_prices (id SERIAL PRIMARY KEY, item_id INTEGER NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE, option_name TEXT, price REAL NOT NULL, is_default BOOLEAN DEFAULT FALSE)""",
        """CREATE TABLE IF NOT EXISTS orders (id SERIAL PRIMARY KEY, daily_sequence_number INTEGER, user_telegram_id BIGINT NOT NULL, total_amount REAL NOT NULL, status TEXT NOT NULL DEFAULT 'new', created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS order_items (id SERIAL PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE, item_name TEXT NOT NULL, category_name TEXT NOT NULL, chosen_price REAL NOT NULL, quantity INTEGER NOT NULL DEFAULT 1, details TEXT)""",
        """CREATE TABLE IF NOT EXISTS bug_reports (id SERIAL PRIMARY KEY, user_telegram_id BIGINT NOT NULL, user_role TEXT, report_text TEXT NOT NULL, reported_at TIMESTAMPTZ DEFAULT now())""",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_cat_name_lower ON menu_categories (lower(name))",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_item_name_lower ON menu_items (category_id, lower(name))"
    ]
    for query in queries:
        await _execute(pool, query)
    logger.info("Проверка таблиц и индексов в PostgreSQL завершена.")


async def _check_and_populate(pool: asyncpg.Pool):
    count = await _execute(pool, "SELECT COUNT(*) FROM menu_categories", fetch='val')
    if count == 0:
        logger.info("Таблицы меню пусты. Заполняю из menu_data...")
        for category_name, items in MENU.items():
            cat_id = await add_menu_category(pool, category_name)
            if cat_id:
                for item_name, item_data in items.items():
                    # <<< ИЗМЕНЕНИЕ: Убрали description при автозаполнении
                    item_id = await add_menu_item(pool, cat_id, item_name)
                    if item_id:
                        prices_list = item_data.get("prices", [])
                        for price_value in prices_list:
                            # <<< ИЗМЕНЕНИЕ: Упростили добавление цены
                            await add_menu_item_price(pool, item_id=item_id, price=price_value, option_name=None)
        logger.info("Заполнение меню завершено.")
    else:
        logger.info(f"В меню уже есть {count} категорий. Пропускаю заполнение.")


async def initialize_database(pool: asyncpg.Pool):
    """Выполняет полную инициализацию базы данных: создает таблицы и заполняет их при необходимости."""
    logger.info("Начинаю инициализацию базы данных...")
    await create_tables(pool)
    await _check_and_populate(pool)
    logger.info("Инициализация базы данных успешно завершена.")


# --- ДАЛЕЕ ВСЕ ФУНКЦИИ МОДИФИЦИРОВАНЫ, ЧТОБЫ ПРИНИМАТЬ `pool` ---
# --- Я НЕ БУДУ ВЫВОДИТЬ ИХ ВСЕ, НО В ИТОГОВОМ КОДЕ ОНИ БУДУТ ---
# --- ПРИМЕР ИЗМЕНЕНИЯ: ---
# БЫЛО: async def add_menu_category(name: str) -> int | None:
# СТАЛО: async def add_menu_category(pool: asyncpg.Pool, name: str) -> int | None:
#            ... await _execute(query, ...) -> await _execute(pool, query, ...)

async def add_menu_category(pool: asyncpg.Pool, name: str, is_active: bool = True, sort_order: int = 0) -> int | None:
    query = "INSERT INTO menu_categories (name, is_active, sort_order) VALUES ($1, $2, $3) RETURNING id"
    try:
        return await _execute(pool, query, name, is_active, sort_order, fetch='val')
    except asyncpg.UniqueViolationError:
        logger.warning(f"Категория с именем '{name}' (без учета регистра) уже существует.");
        return None


async def get_all_menu_categories(pool: asyncpg.Pool, only_active: bool = False) -> list[asyncpg.Record]:
    query = "SELECT * FROM menu_categories";
    if only_active: query += " WHERE is_active = TRUE"
    query += " ORDER BY sort_order, name";
    return await _execute(pool, query, fetch='all')


async def get_menu_category_by_id(pool: asyncpg.Pool, category_id: int) -> asyncpg.Record | None: return await _execute(
    pool, "SELECT * FROM menu_categories WHERE id = $1", category_id, fetch='row')


async def update_menu_category(pool: asyncpg.Pool, category_id: int, name: str = None, is_active: bool = None,
                               sort_order: int = None) -> bool:
    fields, params, param_idx = [], [], 1
    if name is not None: fields.append(f"name = ${param_idx}"); params.append(name); param_idx += 1
    if is_active is not None: fields.append(f"is_active = ${param_idx}"); params.append(is_active); param_idx += 1
    if sort_order is not None: fields.append(f"sort_order = ${param_idx}"); params.append(sort_order); param_idx += 1
    if not fields: return False
    params.append(category_id);
    query = f"UPDATE menu_categories SET {', '.join(fields)} WHERE id = ${param_idx}"
    res = await _execute(pool, query, *params);
    return res and "UPDATE 1" in res


async def delete_menu_category(pool: asyncpg.Pool, category_id: int) -> bool: res = await _execute(
    pool, "DELETE FROM menu_categories WHERE id = $1", category_id); return res and "DELETE 1" in res


async def check_category_name_exists(pool: asyncpg.Pool, name: str, category_id_to_exclude: int = None) -> bool:
    query = "SELECT id FROM menu_categories WHERE lower(name) = lower($1)";
    params = [name]
    if category_id_to_exclude: query += " AND id != $2"; params.append(category_id_to_exclude)
    result = await _execute(pool, query, *params, fetch='val');
    return result is not None


async def add_menu_item(pool: asyncpg.Pool, category_id: int, name: str, description: str = None,
                        is_active: bool = True, sort_order: int = 0) -> int | None:
    query = (
        "INSERT INTO menu_items (category_id, name, description, is_active, sort_order) VALUES ($1, $2, $3, $4, $5) RETURNING id")
    try:
        return await _execute(pool, query, category_id, name, description, is_active, sort_order, fetch='val')
    except asyncpg.UniqueViolationError:
        logger.warning(f"Товар с именем '{name}' в категории {category_id} уже существует.");
        return None


async def get_menu_items_by_category_id(pool: asyncpg.Pool, category_id: int, only_active: bool = False) -> list[
    asyncpg.Record]:
    query = "SELECT * FROM menu_items WHERE category_id = $1"
    if only_active: query += " AND is_active = TRUE"
    query += " ORDER BY sort_order, name";
    return await _execute(pool, query, category_id, fetch='all')


async def get_menu_item_by_id(pool: asyncpg.Pool, item_id: int) -> asyncpg.Record | None: return await _execute(
    pool, "SELECT * FROM menu_items WHERE id = $1", item_id, fetch='row')


async def update_menu_item(pool: asyncpg.Pool, item_id: int, **kwargs) -> bool:
    if not kwargs: return False
    fields, params = [f"{key} = ${i + 1}" for i, key in enumerate(kwargs)], list(kwargs.values());
    params.append(item_id)
    query = f"UPDATE menu_items SET {', '.join(fields)} WHERE id = ${len(kwargs) + 1}";
    res = await _execute(pool, query, *params);
    return res and "UPDATE 1" in res


async def delete_menu_item(pool: asyncpg.Pool, item_id: int) -> bool: res = await _execute(pool,
                                                                                           "DELETE FROM menu_items "
                                                                                           "WHERE id = $1",
                                                                                           item_id); return res and "DELETE 1" in res


async def check_item_name_exists(pool: asyncpg.Pool, category_id: int, item_name: str,
                                 item_id_to_exclude: int = None) -> bool:
    query, params = "SELECT id FROM menu_items WHERE category_id = $1 AND lower(name) = lower($2)", [category_id,
                                                                                                     item_name]
    if item_id_to_exclude: query += " AND id != $3"; params.append(item_id_to_exclude)
    result = await _execute(pool, query, *params, fetch='val');
    return result is not None


async def add_menu_item_price(pool: asyncpg.Pool, item_id: int, price: float, option_name: str = None) -> int | None:
    query = "INSERT INTO menu_item_prices (item_id, price, option_name) VALUES ($1, $2, $3) RETURNING id";
    return await _execute(pool, query, item_id, price, option_name, fetch='val')


async def get_prices_for_menu_item(pool: asyncpg.Pool, item_id: int) -> list[asyncpg.Record]: return await _execute(
    pool, "SELECT * FROM menu_item_prices WHERE item_id = $1 ORDER BY option_name, price", item_id, fetch='all')


async def get_menu_item_price_by_id(pool: asyncpg.Pool, price_id: int) -> asyncpg.Record | None: return await _execute(
    pool, "SELECT * FROM menu_item_prices WHERE id = $1", price_id, fetch='row')


async def update_menu_item_price(pool: asyncpg.Pool, price_id: int, new_price: float = None,
                                 new_option_name: str = None, set_option_name_null: bool = False) -> bool:
    fields, params, param_idx = [], [], 1
    if new_price is not None: fields.append(f"price = ${param_idx}"); params.append(new_price); param_idx += 1
    if set_option_name_null:
        fields.append("option_name = NULL")
    elif new_option_name is not None:
        fields.append(f"option_name = ${param_idx}"); params.append(new_option_name); param_idx += 1
    if not fields: return False
    params.append(price_id);
    query = f"UPDATE menu_item_prices SET {', '.join(fields)} WHERE id = ${param_idx}"
    res = await _execute(pool, query, *params);
    return res and "UPDATE 1" in res


async def delete_menu_item_price(pool: asyncpg.Pool, price_id: int) -> bool: res = await _execute(pool,
                                                                                                  "DELETE FROM "
                                                                                                  "menu_item_prices "
                                                                                                  "WHERE id = $1",
                                                                                                  price_id); return res and "DELETE 1" in res


async def save_order_to_db(pool: asyncpg.Pool, user_telegram_id: int, order_items_list: list[dict],
                           total_amount: float) -> Tuple[int, int] | None:
    async with pool.acquire() as connection:
        async with connection.transaction():
            query_max_daily = "SELECT MAX(daily_sequence_number) FROM orders WHERE created_at::date = now()::date"
            max_today = await connection.fetchval(query_max_daily)
            next_daily_number = (max_today or 0) + 1
            record = await connection.fetchrow(
                "INSERT INTO orders (user_telegram_id, total_amount, daily_sequence_number) VALUES ($1, $2, "
                "$3) RETURNING id, daily_sequence_number",
                user_telegram_id, total_amount, next_daily_number)
            if not record: return None
            order_id, daily_seq_num = record['id'], record['daily_sequence_number']
            if order_items_list:
                items_data = [
                    (order_id, i.get("name"), i.get("category"), i.get("price"), i.get("quantity"), i.get("details"))
                    for i in order_items_list]
                await connection.copy_records_to_table('order_items', columns=['order_id', 'item_name', 'category_name',
                                                                               'chosen_price', 'quantity', 'details'],
                                                       records=items_data)
            return order_id, daily_seq_num


async def update_order_status(pool: asyncpg.Pool, order_id: int, new_status: str) -> bool: res = await _execute(
    pool, "UPDATE orders SET status = $1, updated_at = now() WHERE id = $2", new_status,
    order_id); return res and "UPDATE 1" in res


async def get_orders_by_status(pool: asyncpg.Pool, status: str) -> list[asyncpg.Record]: return await _execute(
    pool, "SELECT * FROM orders WHERE status = $1 ORDER BY created_at ASC", status, fetch='all')


async def get_order_items(pool: asyncpg.Pool, order_id: int) -> list[asyncpg.Record]: return await _execute(
    pool, "SELECT * FROM order_items WHERE order_id = $1", order_id, fetch='all')


async def get_order_by_id(pool: asyncpg.Pool, order_id: int) -> asyncpg.Record | None: return await _execute(
    pool, "SELECT * FROM orders WHERE id = $1", order_id, fetch='row')


async def delete_order_item(pool: asyncpg.Pool, order_item_id: int) -> bool: res = await _execute(pool,
                                                                                                  "DELETE FROM "
                                                                                                  "order_items WHERE "
                                                                                                  "id = $1",
                                                                                                  order_item_id); return res and "DELETE 1" in res


async def recalculate_order_total_amount(pool: asyncpg.Pool, order_id: int) -> float | None:
    new_total = await _execute(pool,
                               "SELECT COALESCE(SUM(chosen_price * quantity), 0) FROM order_items WHERE order_id = $1",
                               order_id, fetch='val')
    await _execute(pool, "UPDATE orders SET total_amount = $1, updated_at = now() WHERE id = $2", new_total, order_id)
    return new_total


async def delete_order(pool: asyncpg.Pool, order_id: int) -> bool: res = await _execute(pool,
                                                                                        "DELETE FROM orders WHERE id "
                                                                                        "= $1",
                                                                                        order_id); return res and "DELETE 1" in res


async def add_item_to_existing_order(pool: asyncpg.Pool, order_id: int, item_name: str, category_name: str,
                                     chosen_price: float, quantity: int, details: str = None) -> int | None:
    query = (
        "INSERT INTO order_items (order_id, item_name, category_name, chosen_price, quantity, details) VALUES ($1, "
        "$2, $3, $4, $5, $6) RETURNING id")
    return await _execute(pool, query, order_id, item_name, category_name, chosen_price, quantity, details, fetch='val')


async def increment_order_item_quantity(pool: asyncpg.Pool, order_item_id: int,
                                        quantity_to_add: int) -> bool: res = await _execute(
    pool, "UPDATE order_items SET quantity = quantity + $1 WHERE id = $2", quantity_to_add,
    order_item_id); return res and "UPDATE 1" in res


async def find_order_item_in_order(pool: asyncpg.Pool, order_id: int, item_name: str,
                                   chosen_price: float) -> asyncpg.Record | None:
    query = "SELECT * FROM order_items WHERE order_id = $1 AND item_name = $2 AND chosen_price = $3"
    return await _execute(pool, query, order_id, item_name, chosen_price, fetch='row')


async def add_items_to_existing_order(pool: asyncpg.Pool, order_id: int, items_to_add: list[dict]) -> bool:
    if not items_to_add: return True
    async with pool.acquire() as connection:
        async with connection.transaction():
            for item in items_to_add:
                existing_item = await find_order_item_in_order(pool, order_id, item['name'], item['price'])
                if existing_item:
                    await increment_order_item_quantity(pool, existing_item['id'], item['quantity'])
                else:
                    await add_item_to_existing_order(pool=pool, order_id=order_id, item_name=item['name'],
                                                     category_name=item['category'], chosen_price=item['price'],
                                                     quantity=item['quantity'])
            await recalculate_order_total_amount(pool, order_id)
    return True


async def get_sales_summary_for_period(pool: asyncpg.Pool, start_date: date, end_date: date) -> tuple:
    query = (
        "SELECT COUNT(id), COALESCE(SUM(total_amount), 0.0) FROM orders WHERE status = 'completed' AND "
        "created_at::date BETWEEN $1 AND $2")
    res = await _execute(pool, query, start_date, end_date, fetch='row');
    return (res[0], res[1]) if res else (0, 0.0)


async def get_sold_items_details_for_period(pool: asyncpg.Pool, start_date: date, end_date: date) -> list:
    query = (
        "SELECT oi.item_name, SUM(oi.quantity) as total_quantity_sold FROM order_items oi JOIN orders o ON "
        "oi.order_id = o.id WHERE o.status = 'completed' AND o.created_at::date BETWEEN $1 AND $2 GROUP BY "
        "oi.item_name ORDER BY total_quantity_sold DESC")
    return await _execute(pool, query, start_date, end_date, fetch='all')


async def save_bug_report(pool: asyncpg.Pool, user_id: int, role: str | None, text: str) -> bool:
    query = "INSERT INTO bug_reports (user_telegram_id, user_role, report_text) VALUES ($1, $2, $3)"
    result = await _execute(pool, query, user_id, role, text)
    return result is not None
