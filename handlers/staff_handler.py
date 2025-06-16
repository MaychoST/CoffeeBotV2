# Имя файла: handlers/staff_handler.py (ФИНАЛЬНАЯ ВЕРСИЯ)

import logging
import asyncpg
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from states import ItemSelectionProcessStates
from constants import (CURRENCY_SYMBOL, VIEW_ACTIVE_ORDERS_TEXT, CB_PREFIX_COMPLETE_ORDER, CB_PREFIX_EDIT_ORDER,
                       CB_PREFIX_EDIT_ORDER_DELETE_PROMPT, CB_PREFIX_EDIT_ORDER_CONFIRM_DELETE,
                       CB_PREFIX_EDIT_ORDER_ADD_ITEM_START, CB_PREFIX_EDIT_ORDER_FINISH)
from utils import _display_active_orders_list, _display_edit_order_interface
from database import (get_order_by_id, delete_order_item, recalculate_order_total_amount, delete_order,
                      update_order_status, get_order_items, get_all_menu_categories)
from keyboards import (get_edit_order_actions_keyboard, get_items_to_delete_keyboard, get_categories_keyboard,
                       get_admin_menu_keyboard, get_barista_menu_keyboard)

router = Router()
logger = logging.getLogger(__name__)


async def check_auth(target: Message | CallbackQuery, state: FSMContext) -> str | None:
    data = await state.get_data();
    role = data.get('role')
    if role not in ['admin', 'barista']:
        if isinstance(target, CallbackQuery):
            await target.answer("Доступ запрещен.", True)
        else:
            await target.answer("Доступ запрещен. Пожалуйста, авторизуйтесь через /start.")
        return None
    return role


@router.message(F.text == VIEW_ACTIVE_ORDERS_TEXT, StateFilter(None))
async def show_active_orders(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    user_role = await check_auth(message, state);
    if not user_role: return
    auth_data = await state.get_data();
    await state.clear();
    await state.set_data(auth_data)
    await _display_active_orders_list(message.bot, db_pool, message.chat.id, user_role)


@router.callback_query(F.data.startswith(CB_PREFIX_COMPLETE_ORDER))
async def process_complete_order_callback(callback_query: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    user_role = await check_auth(callback_query, state);
    if not user_role: return
    try:
        order_id = int(callback_query.data.split(":")[1])
    except (IndexError, ValueError):
        await callback_query.answer("Ошибка ID заказа.", True);
        return

    success = await update_order_status(db_pool, order_id, 'completed')
    if not callback_query.message:
        await callback_query.answer(f"Заказ #{order_id} {'выполнен' if success else 'не обновлен'}.", True);
        return

    if success:
        order = await get_order_by_id(db_pool, order_id)
        daily_num = order['daily_sequence_number'] if order else order_id
        await callback_query.answer(f"Заказ #{daily_num} выполнен!")
        await _display_active_orders_list(callback_query.bot, db_pool, callback_query.message.chat.id, user_role,
                                          callback_query.message.message_id)
    else:
        await callback_query.answer(f"Не удалось обновить статус заказа #{order_id}.", True)
        await _display_active_orders_list(callback_query.bot, db_pool, callback_query.message.chat.id, user_role,
                                          callback_query.message.message_id, False)


@router.callback_query(F.data.startswith(CB_PREFIX_EDIT_ORDER))
async def edit_order_start(callback_query: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_auth(callback_query, state): return
    try:
        order_id = int(callback_query.data.split(":")[1])
    except (IndexError, ValueError):
        await callback_query.answer("Ошибка ID заказа.", True);
        return

    current_data = await state.get_data();
    await state.clear()
    if 'role' in current_data: await state.set_data({'role': current_data['role']})

    if callback_query.message:
        await _display_edit_order_interface(callback_query.message, db_pool, order_id)
    await callback_query.answer()


@router.callback_query(F.data.startswith(CB_PREFIX_EDIT_ORDER_DELETE_PROMPT))
async def edit_order_delete_item_prompt(callback_query: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_auth(callback_query, state): return
    try:
        order_id = int(callback_query.data.split(":")[1])
    except (IndexError, ValueError):
        await callback_query.answer("Ошибка ID заказа.", True);
        return

    order_data = await get_order_by_id(db_pool, order_id)
    if not order_data or order_data['status'] != 'new':
        await callback_query.answer("Заказ нельзя редактировать.", True);
        return

    order_items = await get_order_items(db_pool, order_id)
    if not order_items:
        await callback_query.answer("В заказе нет позиций для удаления.", True)
        if callback_query.message: await _display_edit_order_interface(callback_query.message, db_pool, order_id)
        return

    if callback_query.message:
        daily_num = order_data.get('daily_sequence_number', order_id)
        await callback_query.message.edit_text(f"Какую позицию удалить из Заказа #{daily_num}?",
                                               reply_markup=get_items_to_delete_keyboard(order_items, order_id))
    await callback_query.answer()


@router.callback_query(F.data.startswith(CB_PREFIX_EDIT_ORDER_CONFIRM_DELETE))
async def edit_order_confirm_delete_item_action(callback_query: CallbackQuery, state: FSMContext,
                                                db_pool: asyncpg.Pool):
    user_role = await check_auth(callback_query, state);
    if not user_role: return
    try:
        order_item_id, order_id = map(int, callback_query.data.split(":")[1:])
    except (IndexError, ValueError):
        await callback_query.answer("Ошибка данных.", True);
        return

    if not await delete_order_item(db_pool, order_item_id):
        await callback_query.answer("Не удалось удалить позицию.", True)
        if callback_query.message: await _display_edit_order_interface(callback_query.message, db_pool, order_id)
        return

    remaining_items = await get_order_items(db_pool, order_id)
    if not remaining_items:
        if await delete_order(db_pool, order_id):
            await callback_query.answer("Последняя позиция удалена, заказ аннулирован.", True)
            if callback_query.message: await callback_query.message.delete()
            await _display_active_orders_list(callback_query.bot, db_pool, callback_query.message.chat.id, user_role)
        else:
            await callback_query.answer("Ошибка аннулирования пустого заказа.", True)
            if callback_query.message: await _display_edit_order_interface(callback_query.message, db_pool, order_id)
    else:
        new_total = await recalculate_order_total_amount(db_pool, order_id)
        await callback_query.answer(f"Позиция удалена. Новая сумма: {new_total or 0:.2f} {CURRENCY_SYMBOL}")
        if callback_query.message:
            await _display_edit_order_interface(callback_query.message, db_pool, order_id,
                                                custom_text_prefix="✅ Позиция удалена.")


@router.callback_query(F.data.startswith(CB_PREFIX_EDIT_ORDER_FINISH))
async def edit_order_finish(callback_query: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    user_role = await check_auth(callback_query, state);
    if not user_role: return
    await callback_query.answer("Редактирование завершено.")
    menu_kb = get_admin_menu_keyboard() if user_role == "admin" else get_barista_menu_keyboard()
    if callback_query.message:
        try:
            await callback_query.message.delete()
        except TelegramBadRequest:
            pass
    await callback_query.bot.send_message(callback_query.from_user.id, "Вы вернулись к списку заказов.",
                                          reply_markup=menu_kb)
    await _display_active_orders_list(callback_query.bot, db_pool, callback_query.from_user.id, user_role)


@router.callback_query(F.data.startswith(CB_PREFIX_EDIT_ORDER_ADD_ITEM_START))
async def edit_order_add_item_start_fsm(callback_query: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_auth(callback_query, state): return
    try:
        order_id = int(callback_query.data.split(":")[1])
    except (IndexError, ValueError):
        await callback_query.answer("Ошибка ID заказа.", True);
        return

    order_data_check = await get_order_by_id(db_pool, order_id)
    if not order_data_check or order_data_check['status'] != 'new':
        await callback_query.answer("Этот заказ уже нельзя редактировать.", True);
        return

    categories = await get_all_menu_categories(db_pool, only_active=True)
    if not categories:
        await callback_query.answer("В меню нет активных категорий.", True);
        return

    auth_data = await state.get_data();
    await state.clear();
    await state.set_data(auth_data)
    await state.update_data(process_type="add_to_existing_order", editing_order_id=order_id, order_items=[],
                            total_amount=0.0)

    if callback_query.message: await callback_query.message.delete()

    daily_num = order_data_check.get('daily_sequence_number', order_id)
    await callback_query.bot.send_message(callback_query.from_user.id,
                                          f"🛒 Добавление товара в заказ #{daily_num}...\nВыберите категорию:",
                                          reply_markup=get_categories_keyboard([cat['name'] for cat in categories]))
    await state.set_state(ItemSelectionProcessStates.choosing_category)
    await callback_query.answer()
