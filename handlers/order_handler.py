# handlers/order_handler.py
import logging
from aiogram import Router, F, html
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.types import Message, ReplyKeyboardRemove

from states import ItemSelectionProcessStates
from keyboards import (
    get_categories_keyboard, get_items_keyboard, get_price_options_keyboard,
    get_quantity_keyboard, get_order_actions_keyboard, get_manual_input_cancel_keyboard,
    get_admin_menu_keyboard, get_barista_menu_keyboard
)
from database import (
    get_all_menu_categories, get_menu_items_by_category_id, get_prices_for_menu_item,
    save_order_to_db, add_items_to_existing_order  # ИЗМЕНЕНИЕ
)
from constants import (
    CREATE_ORDER_TEXT, CURRENCY_SYMBOL, CANCEL_ORDER_CREATION_TEXT, OTHER_QUANTITY_TEXT,
    VIEW_CURRENT_ORDER_TEXT, ADD_MORE_TO_ORDER_TEXT, COMPLETE_AND_SAVE_ORDER_TEXT,
    CANCEL_IN_PROGRESS_ORDER_TEXT, GENERAL_CANCEL_TEXT
)
from utils import _display_edit_order_interface  # ИЗМЕНЕНИЕ

router = Router()
logger = logging.getLogger(__name__)


async def check_auth(target: Message, state: FSMContext) -> str | None:
    """Проверяет авторизацию и возвращает роль, или None если не авторизован."""
    data = await state.get_data()
    role = data.get('role')
    if role not in ['admin', 'barista']:
        await target.answer("Доступ запрещен. Пожалуйста, авторизуйтесь через /start.")
        return None
    return role


def format_order_text(order_items: list, total_amount: float) -> str:
    """Форматирует текст с составом и суммой заказа."""
    if not order_items:
        return "🛒 Ваш заказ пока пуст."
    text = "<b>🛒 Ваш текущий заказ:</b>\n\n"
    for item in order_items:
        item_total = item['price'] * item['quantity']
        text += f"- {html.quote(item['name'])} ({item['price']:.2f} {CURRENCY_SYMBOL}) x {item['quantity']} = {item_total:.2f}\n"
    text += f"\n💰 <b>Итого: {total_amount:.2f} {CURRENCY_SYMBOL}</b>"
    return text


async def add_item_to_state(state: FSMContext, item_name: str, category_name: str, price: float, quantity: int):
    """Добавляет или обновляет товар в корзине внутри FSM state."""
    data = await state.get_data()
    order_items = data.get('order_items', [])
    found = False
    for item in order_items:
        if item['name'] == item_name and item['price'] == price:
            item['quantity'] += quantity;
            found = True;
            break
    if not found:
        order_items.append({"name": item_name, "category": category_name, "price": price, "quantity": quantity})
    total_amount = sum(it['price'] * it['quantity'] for it in order_items)
    await state.update_data(order_items=order_items, total_amount=total_amount)


@router.message(F.text == CREATE_ORDER_TEXT, StateFilter(None))
async def start_order_creation(message: Message, state: FSMContext):
    if not await check_auth(message, state): return
    categories = await get_all_menu_categories(only_active=True)
    if not categories:
        await message.answer("Извините, в меню пока нет активных категорий для заказа.");
        return
    auth_data = await state.get_data()
    await state.clear()
    await state.set_data(auth_data)
    await state.set_state(ItemSelectionProcessStates.choosing_category)
    await state.update_data(order_items=[], total_amount=0.0)
    await message.answer("Начинаем сборку заказа! Выберите категорию:",
                         reply_markup=get_categories_keyboard([cat['name'] for cat in categories]))


@router.message(ItemSelectionProcessStates.choosing_category, F.text)
async def process_category_choice(message: Message, state: FSMContext):
    if message.text == CANCEL_ORDER_CREATION_TEXT:
        role = await check_auth(message, state)
        if not role: return
        data = await state.get_data()
        editing_order_id = data.get('editing_order_id')
        await state.clear();
        await state.set_data({'role': role})  # Безопасный сброс
        if editing_order_id:
            await message.answer("Добавление отменено.", reply_markup=ReplyKeyboardRemove())
            await _display_edit_order_interface(message.bot, editing_order_id, chat_id_for_new=message.chat.id)
        else:
            menu_kb = get_admin_menu_keyboard() if role == "admin" else get_barista_menu_keyboard()
            await message.answer("Создание заказа отменено.", reply_markup=menu_kb)
        return

    categories = await get_all_menu_categories(only_active=True)
    chosen_category = next((cat for cat in categories if cat['name'] == message.text), None)
    if not chosen_category:
        await message.answer("Пожалуйста, выберите категорию с помощью кнопок.");
        return

    items = await get_menu_items_by_category_id(chosen_category['id'], only_active=True)
    if not items:
        await message.answer("В этой категории нет доступных товаров. Выберите другую.");
        return

    await state.update_data(chosen_category_name=chosen_category['name'], chosen_category_id=chosen_category['id'])
    await state.set_state(ItemSelectionProcessStates.choosing_item)
    items_text = [f"{item['name']}" for item in items]
    await message.answer("Отлично! Выберите товар:",
                         reply_markup=get_items_keyboard(items_text, chosen_category['name']))


@router.message(ItemSelectionProcessStates.choosing_item, F.text)
async def process_item_choice(message: Message, state: FSMContext):
    data = await state.get_data()
    category_id = data.get('chosen_category_id')
    category_name = data.get('chosen_category_name')
    if message.text.startswith("🔙 К категориям"):
        categories = await get_all_menu_categories(only_active=True)
        await state.set_state(ItemSelectionProcessStates.choosing_category)
        await message.answer("К выбору категории:",
                             reply_markup=get_categories_keyboard([cat['name'] for cat in categories]))
        return
    items_in_category = await get_menu_items_by_category_id(category_id, only_active=True)
    chosen_item = next((item for item in items_in_category if item['name'] == message.text), None)
    if not chosen_item:
        await message.answer("Пожалуйста, выберите товар с помощью кнопок.");
        return

    prices = await get_prices_for_menu_item(chosen_item['id'])
    await state.update_data(pending_item_name=chosen_item['name'])
    if len(prices) == 1:
        await state.update_data(pending_item_price=prices[0]['price'])
        await state.set_state(ItemSelectionProcessStates.choosing_quantity)
        await message.answer(f"Товар: <b>{html.quote(chosen_item['name'])}</b>.\nКол-во:",
                             reply_markup=get_quantity_keyboard(f"🔙 К товарам ({category_name})"), parse_mode="HTML")
    else:
        await state.set_state(ItemSelectionProcessStates.choosing_price_option)
        await message.answer(f"Товар: <b>{html.quote(chosen_item['name'])}</b>.\nЦена/опция:",
                             reply_markup=get_price_options_keyboard([p['price'] for p in prices], chosen_item['name'],
                                                                     category_name), parse_mode="HTML")


@router.message(ItemSelectionProcessStates.choosing_price_option, F.text)
async def process_price_choice(message: Message, state: FSMContext):
    data = await state.get_data()
    item_name, category_name = data.get('pending_item_name'), data.get('chosen_category_name')
    if message.text.startswith("🔙 К товарам"):
        await state.set_state(ItemSelectionProcessStates.choosing_item)
        items = await get_menu_items_by_category_id(data['chosen_category_id'], only_active=True)
        await message.answer("К выбору товара:",
                             reply_markup=get_items_keyboard([i['name'] for i in items], category_name));
        return
    try:
        chosen_price = float(message.text.split(" ")[0])
    except (ValueError, IndexError):
        await message.answer("Используйте кнопки для выбора цены.");
        return
    await state.update_data(pending_item_price=chosen_price)
    await state.set_state(ItemSelectionProcessStates.choosing_quantity)
    await message.answer(f"Выбрана цена {chosen_price:.2f} {CURRENCY_SYMBOL}.\nТеперь введите количество:",
                         reply_markup=get_quantity_keyboard(f"🔙 К опциям ({item_name})"))


@router.message(ItemSelectionProcessStates.choosing_quantity, F.text)
async def process_quantity_choice(message: Message, state: FSMContext):
    data = await state.get_data()
    item_name, item_price = data.get('pending_item_name'), data.get('pending_item_price')
    category_name, category_id = data.get('chosen_category_name'), data.get('chosen_category_id')
    if message.text.startswith("🔙"):
        await state.set_state(ItemSelectionProcessStates.choosing_item)
        items = await get_menu_items_by_category_id(category_id, only_active=True)
        items_text = [f"{item['name']}" for item in items]
        await message.answer(f"Возврат к выбору товара в категории '{category_name}':",
                             reply_markup=get_items_keyboard(items_text, category_name))
        return
    if message.text == OTHER_QUANTITY_TEXT:
        await state.set_state(ItemSelectionProcessStates.waiting_for_manual_quantity)
        await message.answer("Введите количество вручную:", reply_markup=get_manual_input_cancel_keyboard());
        return
    try:
        quantity = int(message.text);
        assert 1 <= quantity <= 99
    except (ValueError, AssertionError):
        await message.answer("Пожалуйста, выберите количество с помощью кнопок или введите число от 1 до 99.");
        return
    await add_item_to_state(state, item_name, category_name, item_price, quantity)
    await state.set_state(None)
    await message.answer(f"✅ Добавлено: {html.quote(item_name)} ({item_price:.2f} {CURRENCY_SYMBOL}) x{quantity}",
                         reply_markup=get_order_actions_keyboard())


@router.message(ItemSelectionProcessStates.waiting_for_manual_quantity, F.text)
async def process_manual_quantity(message: Message, state: FSMContext):
    if message.text == GENERAL_CANCEL_TEXT:
        await state.set_state(ItemSelectionProcessStates.choosing_quantity)
        await message.answer("Ручной ввод отменен. Выберите количество:", reply_markup=get_quantity_keyboard());
        return
    try:
        quantity = int(message.text);
        assert 1 <= quantity <= 99
    except (ValueError, AssertionError):
        await message.answer("Неверный формат. Введите число от 1 до 99.",
                             reply_markup=get_manual_input_cancel_keyboard());
        return
    data = await state.get_data()
    item_name, item_price = data.get('pending_item_name'), data.get('pending_item_price')
    category_name = data.get('chosen_category_name')
    await add_item_to_state(state, item_name, category_name, item_price, quantity)
    await state.set_state(None)
    await message.answer(f"✅ Добавлено: {html.quote(item_name)} ({item_price:.2f} {CURRENCY_SYMBOL}) x{quantity}",
                         reply_markup=get_order_actions_keyboard())


@router.message(F.text == ADD_MORE_TO_ORDER_TEXT, StateFilter(None))
async def add_more_to_order(message: Message, state: FSMContext):
    if not await check_auth(message, state): return
    categories = await get_all_menu_categories(only_active=True)
    await state.set_state(ItemSelectionProcessStates.choosing_category)
    await message.answer("Выберите категорию для следующего товара:",
                         reply_markup=get_categories_keyboard([cat['name'] for cat in categories]))


@router.message(F.text == VIEW_CURRENT_ORDER_TEXT, StateFilter(None))
async def view_current_order(message: Message, state: FSMContext):
    if not await check_auth(message, state): return
    data = await state.get_data()
    order_text = format_order_text(data.get('order_items', []), data.get('total_amount', 0.0))
    await message.answer(order_text, reply_markup=get_order_actions_keyboard())


@router.message(F.text == CANCEL_IN_PROGRESS_ORDER_TEXT, StateFilter(None))
async def cancel_full_order(message: Message, state: FSMContext):
    role = await check_auth(message, state)
    if not role: return
    data = await state.get_data()
    editing_order_id = data.get('editing_order_id')
    await state.clear();
    await state.set_data({'role': role})
    if editing_order_id:
        await message.answer("Добавление отменено.", reply_markup=ReplyKeyboardRemove())
        await _display_edit_order_interface(message.bot, editing_order_id, chat_id_for_new=message.chat.id)
    else:
        menu_kb = get_admin_menu_keyboard() if role == "admin" else get_barista_menu_keyboard()
        await message.answer("Текущий заказ полностью отменен.", reply_markup=menu_kb)


# --- ГЛАВНОЕ ИЗМЕНЕНИЕ ---
@router.message(F.text == COMPLETE_AND_SAVE_ORDER_TEXT, StateFilter(None))
async def complete_and_save_order(message: Message, state: FSMContext):
    role = await check_auth(message, state)
    if not role: return

    data = await state.get_data()
    order_items = data.get('order_items', [])
    total_amount = data.get('total_amount', 0.0)
    process_type = data.get('process_type')
    editing_order_id = data.get('editing_order_id')

    if not order_items:
        await message.answer("Вы ничего не добавили, нечего сохранять.", reply_markup=get_order_actions_keyboard());
        return

    # --- ЛОГИКА ДЛЯ РЕДАКТИРОВАНИЯ СУЩЕСТВУЮЩЕГО ЗАКАЗА ---
    if process_type == "add_to_existing_order" and editing_order_id:
        success = await add_items_to_existing_order(editing_order_id, order_items)
        if success:
            await message.answer(f"✅ Позиции успешно добавлены в заказ #{editing_order_id}!",
                                 reply_markup=ReplyKeyboardRemove())
            # Безопасно сбрасываем состояние и показываем обновленный интерфейс редактирования
            await state.clear();
            await state.set_data({'role': role})
            await _display_edit_order_interface(message.bot, editing_order_id, chat_id_for_new=message.chat.id)
        else:
            await message.answer("❌ Произошла ошибка при добавлении позиций. Попробуйте снова.",
                                 reply_markup=get_order_actions_keyboard())

    # --- ЛОГИКА ДЛЯ СОЗДАНИЯ НОВОГО ЗАКАЗА (стандартное поведение) ---
    else:
        saved_order_id = await save_order_to_db(message.from_user.id, order_items, total_amount)
        if saved_order_id:
            order_summary = format_order_text(order_items, total_amount).replace("Ваш текущий заказ",
                                                                                 f"Заказ #{saved_order_id} оформлен")
            await message.answer(order_summary, reply_markup=ReplyKeyboardRemove())
            # Сбрасываем все, кроме авторизации
            await state.clear();
            await state.set_data({'role': role})
            menu_kb = get_admin_menu_keyboard() if role == "admin" else get_barista_menu_keyboard()
            await message.answer("Что бы вы хотели сделать дальше?", reply_markup=menu_kb)
        else:
            await message.answer("❌ Произошла ошибка при сохранении заказа. Попробуйте снова.",
                                 reply_markup=get_order_actions_keyboard())
