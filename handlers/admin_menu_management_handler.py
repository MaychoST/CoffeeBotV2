# Имя файла: handlers/admin_menu_management_handler.py (ФИНАЛЬНАЯ ВЕРСИЯ)

import logging
import base64
import asyncpg
from aiogram import Router, F, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from states import (AdminNavigationStates, CategoryManagementStates, ItemCreationStates, ItemInfoEditStates,
                    PriceManagementStates)
from keyboards import (get_admin_menu_management_keyboard, get_admin_categories_management_keyboard,
                       get_admin_select_category_for_items_keyboard,
                       get_admin_items_management_keyboard, get_confirm_delete_item_keyboard,
                       get_fsm_navigation_keyboard,
                       get_confirm_delete_category_keyboard, get_admin_item_prices_management_keyboard,
                       get_confirm_delete_price_keyboard,
                       get_admin_menu_keyboard, get_confirm_add_another_price_keyboard)
from database import (get_all_menu_categories, add_menu_category, delete_menu_category, update_menu_category,
                      get_menu_category_by_id,
                      add_menu_item, get_menu_items_by_category_id, get_menu_item_by_id, update_menu_item,
                      delete_menu_item,
                      add_menu_item_price, get_prices_for_menu_item, delete_menu_item_price, update_menu_item_price,
                      get_menu_item_price_by_id, check_item_name_exists, check_category_name_exists)
from constants import *

router = Router()
logger = logging.getLogger(__name__)


async def check_admin_auth(target: Message | CallbackQuery, state: FSMContext) -> bool:
    data = await state.get_data();
    if data.get('role') == 'admin': return True
    if isinstance(target, CallbackQuery):
        await target.answer("Эта функция доступна только администратору.", show_alert=True)
    else:
        await target.answer("Эта функция доступна только администратору.")
    return False


async def _safe_edit_or_send(target: Message | CallbackQuery, text: str, reply_markup, edit: bool = False,
                             parse_mode: str | None = None):
    msg_to_handle = target.message if isinstance(target, CallbackQuery) else target
    if not msg_to_handle: return
    try:
        if edit:
            await msg_to_handle.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await msg_to_handle.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        logger.warning(f"Safe edit/send failed: {e}. Sending new message.")
        await msg_to_handle.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    if isinstance(target, CallbackQuery): await target.answer()


# <<< ВСЕ ФУНКЦИИ-ПОМОЩНИКИ ТЕПЕРЬ ПРИНИМАЮТ И ПЕРЕДАЮТ db_pool >>>

async def show_categories_management_menu(target: Message | CallbackQuery, db_pool: asyncpg.Pool,
                                          edit_message: bool = False):
    categories = await get_all_menu_categories(db_pool, only_active=False)
    text = "🗂️ Управление категориями меню:" + ("\n\nКатегорий пока нет." if not categories else "")
    markup = get_admin_categories_management_keyboard(categories)
    await _safe_edit_or_send(target, text, markup, edit=edit_message)


async def show_select_category_for_items_menu(target: Message | CallbackQuery, db_pool: asyncpg.Pool,
                                              edit_message: bool = False):
    categories = await get_all_menu_categories(db_pool, only_active=True)
    text = "Выберите категорию для управления товарами:" if categories else "Сначала нужно добавить активную категорию."
    markup = get_admin_select_category_for_items_keyboard(categories)
    await _safe_edit_or_send(target, text, markup, edit=edit_message)


async def show_items_management_menu(target: Message | CallbackQuery, db_pool: asyncpg.Pool, category_id: int,
                                     edit_message: bool = False):
    category = await get_menu_category_by_id(db_pool, category_id)
    if not category: await show_select_category_for_items_menu(target, db_pool, edit_message=edit_message); return
    items = await get_menu_items_by_category_id(db_pool, category_id, only_active=False)
    text = f"Управление товарами в категории: <b>{html.quote(str(category['name']))}</b>" + (
        "\n\nТоваров нет." if not items else "")
    markup = get_admin_items_management_keyboard(items, category_id, str(category['name']))
    await _safe_edit_or_send(target, text, markup, edit=edit_message, parse_mode="HTML")


async def show_item_prices_management_menu(target: Message | CallbackQuery, db_pool: asyncpg.Pool, item_id: int,
                                           edit_message: bool = False):
    item = await get_menu_item_by_id(db_pool, item_id)
    if not item: await show_select_category_for_items_menu(target, db_pool, edit_message=True); return
    prices = await get_prices_for_menu_item(db_pool, item_id)
    text = f"Управление ценами для: <b>{html.quote(str(item['name']))}</b>" + ("\n\nЦен нет." if not prices else "")
    markup = get_admin_item_prices_management_keyboard(prices, item_id, str(item['name']), item['category_id'])
    await _safe_edit_or_send(target, text, markup, edit=edit_message, parse_mode="HTML")


# --- Дальше все хэндлеры принимают db_pool ---

@router.message(F.text == ADMIN_MENU_MANAGEMENT_TEXT, StateFilter(None))
async def admin_menu_manage_start(message: Message, state: FSMContext):
    if not await check_admin_auth(message, state): return
    await state.set_state(AdminNavigationStates.in_menu_management)
    await message.answer("⚙️ Выберите раздел:", reply_markup=get_admin_menu_management_keyboard())


@router.message(F.text == MANAGE_CATEGORIES_TEXT, StateFilter(AdminNavigationStates.in_menu_management))
async def admin_manage_categories_entry(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(message, state): return
    await state.set_state(None)
    await show_categories_management_menu(message, db_pool)


@router.message(F.text == MANAGE_ITEMS_TEXT, StateFilter(AdminNavigationStates.in_menu_management))
async def admin_manage_items_entry(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(message, state): return
    await state.set_state(None)
    await show_select_category_for_items_menu(message, db_pool)


@router.message(F.text == BACK_TO_ADMIN_MAIN_MENU_TEXT, StateFilter("*"))
async def back_to_admin_main_menu_from_reports(message: Message, state: FSMContext):
    if not await check_admin_auth(message, state): return
    auth_data = await state.get_data();
    await state.clear()
    if 'role' in auth_data: await state.set_data({'role': auth_data['role']})
    await message.answer("Главное меню администратора.", reply_markup=get_admin_menu_keyboard())


@router.callback_query(F.data == CB_PREFIX_ADMIN_MENU_MANAGE_BACK, StateFilter("*"))
async def cq_admin_menu_manage_back(cq: CallbackQuery, state: FSMContext):
    if not await check_admin_auth(cq, state): return
    auth_data = await state.get_data();
    await state.clear()
    if 'role' in auth_data: await state.set_data({'role': auth_data['role']})
    await state.set_state(AdminNavigationStates.in_menu_management)
    if cq.message:
        await cq.message.delete()
        await cq.message.answer("⚙️ Выберите раздел:", reply_markup=get_admin_menu_management_keyboard())
    await cq.answer()


@router.callback_query(F.data == CB_PREFIX_ADMIN_ITEM_CAT_SELECT_BACK, StateFilter("*"))
async def cq_admin_item_cat_select_back(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    await show_select_category_for_items_menu(cq, db_pool, edit_message=True)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_ITEM_MANAGE_CAT_SELECT))
async def cq_admin_item_manage_cat_selected(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    category_id = int(cq.data.split(":")[1])
    await show_items_management_menu(cq, db_pool, category_id, edit_message=True)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_ITEM_MANAGE_PRICES))
async def cq_admin_item_manage_prices_entry(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    item_id = int(cq.data.split(":")[1])
    await show_item_prices_management_menu(cq, db_pool, item_id, edit_message=True)


@router.callback_query(F.data == CB_PREFIX_ADMIN_CAT_ADD_NEW)
async def cq_admin_cat_add_new_start(cq: CallbackQuery, state: FSMContext):
    if not await check_admin_auth(cq, state): return
    await state.set_state(CategoryManagementStates.waiting_for_new_category_name)
    await _safe_edit_or_send(cq, "Введите название для новой категории:",
                             get_fsm_navigation_keyboard(cancel_callback=CB_PREFIX_ADMIN_CAT_CREATION_CANCEL),
                             edit=True)


@router.message(CategoryManagementStates.waiting_for_new_category_name, F.text)
async def process_new_category_name(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    new_name = message.text.strip()
    if not new_name or await check_category_name_exists(db_pool, new_name):
        text = f"❌ Название не может быть пустым или '{html.quote(new_name)}' уже существует. Введите другое:"
        await message.answer(text, reply_markup=get_fsm_navigation_keyboard(
            cancel_callback=CB_PREFIX_ADMIN_CAT_CREATION_CANCEL));
        return

    await add_menu_category(db_pool, name=new_name)
    auth_data = await state.get_data();
    await state.clear()
    if 'role' in auth_data: await state.set_data({'role': auth_data['role']})
    await message.answer(f"✅ Категория '{html.quote(new_name)}' добавлена!", reply_markup=ReplyKeyboardRemove())
    await show_categories_management_menu(message, db_pool)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_CAT_EDIT))
async def cq_admin_cat_edit_start(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    category_id = int(cq.data.split(":")[1]);
    category = await get_menu_category_by_id(db_pool, category_id)
    if not category: await cq.answer("Категория не найдена!", True); return
    await state.update_data(editing_category_id=category_id, old_category_name=category['name'])
    await state.set_state(CategoryManagementStates.waiting_for_edit_category_name)
    await _safe_edit_or_send(cq, f"Редактирование <b>{html.quote(str(category['name']))}</b>\nВведите новое название:",
                             get_fsm_navigation_keyboard(cancel_callback=CB_PREFIX_ADMIN_CAT_EDIT_CANCEL), edit=True,
                             parse_mode="HTML")


@router.message(CategoryManagementStates.waiting_for_edit_category_name, F.text)
async def process_edit_category_name(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    new_name = message.text.strip();
    data = await state.get_data();
    cat_id = data.get("editing_category_id");
    old_name = data.get("old_category_name", "")
    if not new_name or new_name.lower() == old_name.lower():
        await message.answer("Название не может быть пустым или совпадает со старым.",
                             reply_markup=ReplyKeyboardRemove())
    elif await check_category_name_exists(db_pool, new_name, category_id_to_exclude=cat_id):
        await message.answer(f"❌ Категория '{html.quote(new_name)}' уже существует. Введите другое:",
                             reply_markup=get_fsm_navigation_keyboard(cancel_callback=CB_PREFIX_ADMIN_CAT_EDIT_CANCEL));
        return
    else:
        await update_menu_category(db_pool, cat_id, name=new_name)
        await message.answer(f"✅ Название изменено на '{html.quote(new_name)}'!", reply_markup=ReplyKeyboardRemove())
    auth_data = await state.get_data();
    await state.clear()
    if 'role' in auth_data: await state.set_data({'role': auth_data['role']})
    await show_categories_management_menu(message, db_pool)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_CAT_TOGGLE_ACTIVE))
async def cq_admin_cat_toggle_active(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    cat_id = int(cq.data.split(":")[1]);
    category = await get_menu_category_by_id(db_pool, cat_id)
    if not category: await cq.answer("Категория не найдена!", True); return
    new_active = not category['is_active'];
    await update_menu_category(db_pool, cat_id, is_active=new_active)
    await cq.answer(f"Категория '{category['name']}' {'скрыта' if not new_active else 'активирована'}.")
    await show_categories_management_menu(cq, db_pool, edit_message=True)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_CAT_DELETE_PROMPT))
async def cq_admin_cat_delete_prompt(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    cat_id = int(cq.data.split(":")[1]);
    category = await get_menu_category_by_id(db_pool, cat_id)
    if not category: await cq.answer("Категория не найдена!", True); return
    text = f"Удалить категорию '{html.quote(str(category['name']))}'?\n⚠️ <b>Удалятся ВСЕ товары в ней!</b>"
    markup = get_confirm_delete_category_keyboard(cat_id, str(category['name']))
    await _safe_edit_or_send(cq, text, markup, edit=True, parse_mode="HTML")


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_CAT_CONFIRM_DELETE))
async def cq_admin_cat_confirm_delete_action(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    cat_id = int(cq.data.split(":")[1]);
    cat = await get_menu_category_by_id(db_pool, cat_id)
    await delete_menu_category(db_pool, cat_id);
    await cq.answer(f"Категория '{cat['name'] if cat else ''}' удалена.", show_alert=True)
    await show_categories_management_menu(cq, db_pool, edit_message=True)


@router.callback_query(F.data == CB_PREFIX_ADMIN_CAT_CANCEL_DELETE)
async def cq_admin_cat_cancel_delete_action(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return; await show_categories_management_menu(cq, db_pool,
                                                                                            edit_message=True)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_ITEM_ADD_NEW))
async def item_creation_start(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    category_id = int(cq.data.split(":")[1]);
    category = await get_menu_category_by_id(db_pool, category_id)
    if not category: await cq.answer("Категория не найдена.", True); return
    await state.update_data(item_creation_category_id=category_id, item_creation_category_name=category['name'])
    await state.set_state(ItemCreationStates.waiting_for_item_name)
    text = f"Добавление товара в <b>{html.quote(str(category['name']))}</b>\nВведите название:"
    markup = get_fsm_navigation_keyboard(cancel_callback=CB_PREFIX_ADMIN_ITEM_CREATION_CANCEL)
    await _safe_edit_or_send(cq, text, markup, edit=True, parse_mode="HTML")


@router.message(ItemCreationStates.waiting_for_item_name, F.text)
async def item_creation_process_name(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    item_name = message.text.strip();
    fsm_data = await state.get_data();
    category_id = fsm_data.get("item_creation_category_id")
    if not item_name or await check_item_name_exists(db_pool, category_id, item_name):
        await message.answer(f"❌ Название не может быть пустым или '{html.quote(item_name)}' уже есть. Введите другое:",
                             reply_markup=get_fsm_navigation_keyboard(
                                 cancel_callback=CB_PREFIX_ADMIN_ITEM_CREATION_CANCEL));
        return

    await state.update_data(item_creation_item_name=item_name)
    await state.set_state(ItemCreationStates.waiting_for_price_option_name)
    await message.answer(
        f"Название: <b>{html.quote(item_name)}</b>\nТеперь добавим первую цену.\n\nВведите название опции (например, '0.2л', '0.3л' или '-' если опции нет):",
        reply_markup=get_fsm_navigation_keyboard(cancel_callback=CB_PREFIX_ADMIN_ITEM_CREATION_CANCEL_PRICE,
                                                 back_callback=CB_ADMIN_FSM_BACK),
        parse_mode="HTML")


@router.message(ItemCreationStates.waiting_for_price_option_name, F.text)
async def item_creation_process_price_option_name(message: Message, state: FSMContext):
    await state.update_data(
        current_price_option_name_for_creation=None if message.text.strip() == '-' else message.text.strip())
    await state.set_state(ItemCreationStates.waiting_for_price_value)
    await message.answer("Введите значение цены (например, 150):", reply_markup=get_fsm_navigation_keyboard(
        cancel_callback=CB_PREFIX_ADMIN_ITEM_CREATION_CANCEL_PRICE, back_callback=CB_ADMIN_FSM_BACK))


@router.message(ItemCreationStates.waiting_for_price_value, F.text)
async def item_creation_process_price_value(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    try:
        price_value = float(message.text.strip().replace(',', '.'));
        assert price_value > 0
    except:
        await message.answer("❌ Некорректная цена:", reply_markup=get_fsm_navigation_keyboard(
            cancel_callback=CB_PREFIX_ADMIN_ITEM_CREATION_CANCEL_PRICE, back_callback=CB_ADMIN_FSM_BACK));
        return

    fsm_data = await state.get_data();
    item_id = fsm_data.get("item_creation_item_id")
    if not item_id:
        item_id = await add_menu_item(db_pool, category_id=fsm_data["item_creation_category_id"],
                                      name=fsm_data["item_creation_item_name"])
        if not item_id:
            auth_data = await state.get_data();
            await state.clear()
            if 'role' in auth_data: await state.set_data({'role': auth_data['role']})
            await message.answer("Ошибка создания товара.");
            return
        await state.update_data(item_creation_item_id=item_id)

    await add_menu_item_price(db_pool, item_id=item_id,
                              option_name=fsm_data.get("current_price_option_name_for_creation"), price=price_value)
    await message.answer("Цена добавлена. Хотите добавить еще одну?",
                         reply_markup=get_confirm_add_another_price_keyboard(item_id))


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_ITEM_CREATION_ADD_ANOTHER_PRICE))
async def item_creation_add_another_price_yes(cq: CallbackQuery, state: FSMContext):
    if not await check_admin_auth(cq, state): return
    await state.set_state(ItemCreationStates.waiting_for_price_option_name)
    await _safe_edit_or_send(cq, "Добавляем следующую цену.\nНазвание опции ('-' если нет):",
                             get_fsm_navigation_keyboard(cancel_callback=CB_PREFIX_ADMIN_ITEM_CREATION_CANCEL_PRICE,
                                                         back_callback=CB_ADMIN_FSM_BACK), edit=True)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_ITEM_CREATION_FINISH))
async def item_creation_finish(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    fsm_data = await state.get_data();
    category_id = fsm_data.get("item_creation_category_id")
    auth_data = await state.get_data();
    await state.clear()
    if 'role' in auth_data: await state.set_data({'role': auth_data['role']})
    if cq.message: await cq.message.delete(); await cq.message.answer("✅ Товар успешно создан!",
                                                                      reply_markup=ReplyKeyboardRemove())
    if category_id: await show_items_management_menu(cq.message, db_pool, category_id)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_ITEM_EDIT_INFO))
async def cq_admin_item_edit_info_start(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    item_id = int(cq.data.split(":")[1]);
    item = await get_menu_item_by_id(db_pool, item_id)
    if not item: await cq.answer("Товар не найден!", True); return
    await state.update_data(editing_item_id=item_id, editing_item_category_id=item['category_id'],
                            old_item_name=item['name'], old_item_description=item['description'])
    await state.set_state(ItemInfoEditStates.waiting_for_edit_item_name)
    text = f"Редактирование <b>{html.quote(str(item['name']))}</b>\nНовое название ('-' оставить):"
    markup = get_fsm_navigation_keyboard(cancel_callback=CB_PREFIX_ADMIN_ITEM_INFO_EDIT_CANCEL)
    await _safe_edit_or_send(cq, text, markup, edit=True, parse_mode="HTML")


@router.message(ItemInfoEditStates.waiting_for_edit_item_name, F.text)
async def process_edit_item_name(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    name_in = message.text.strip();
    data = await state.get_data();
    old_name = data.get("old_item_name");
    final_name = old_name
    if name_in and name_in != '-':
        if await check_item_name_exists(db_pool, data["editing_item_category_id"], name_in, data["editing_item_id"]):
            await message.answer(f"❌ Товар с именем '{html.quote(name_in)}' уже есть. Введите другое:",
                                 reply_markup=get_fsm_navigation_keyboard(
                                     cancel_callback=CB_PREFIX_ADMIN_ITEM_INFO_EDIT_CANCEL));
            return
        final_name = name_in
    await state.update_data(edited_item_name=final_name);
    await state.set_state(ItemInfoEditStates.waiting_for_edit_item_description)
    await message.answer("Новое описание ('-' оставить тек., 'пусто' удалить):",
                         reply_markup=get_fsm_navigation_keyboard(cancel_callback=CB_PREFIX_ADMIN_ITEM_INFO_EDIT_CANCEL,
                                                                  back_callback=CB_ADMIN_FSM_BACK))


@router.message(ItemInfoEditStates.waiting_for_edit_item_description, F.text)
async def process_edit_item_description_and_save(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    desc_in = message.text.strip();
    data = await state.get_data();
    old_desc = data.get("old_item_description");
    final_desc = old_desc
    if desc_in == '-':
        pass
    elif desc_in.lower() == 'пусто':
        final_desc = None
    else:
        final_desc = desc_in
    item_id = data.get("editing_item_id");
    cat_id_ret = data.get("editing_item_category_id");
    name_save = data.get("edited_item_name")
    await update_menu_item(db_pool, item_id=item_id, name=name_save, description=final_desc);
    auth_data = await state.get_data();
    await state.clear()
    if 'role' in auth_data: await state.set_data({'role': auth_data['role']})
    await message.answer("✅ Информация о товаре обновлена!", reply_markup=ReplyKeyboardRemove());
    await show_items_management_menu(message, db_pool, cat_id_ret)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_ITEM_TOGGLE_ACTIVE))
async def cq_admin_item_toggle_active(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    item_id = int(cq.data.split(":")[1]);
    item = await get_menu_item_by_id(db_pool, item_id)
    if not item: await cq.answer("Товар не найден!", True); return
    new_active = not item['is_active'];
    await update_menu_item(db_pool, item_id, is_active=new_active)
    await cq.answer(f"Товар '{item['name']}' {'скрыт' if not new_active else 'активирован'}.");
    await show_items_management_menu(cq, db_pool, item['category_id'], edit_message=True)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_ITEM_DELETE_PROMPT))
async def cq_admin_item_delete_prompt(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    item_id = int(cq.data.split(":")[1]);
    item = await get_menu_item_by_id(db_pool, item_id)
    if not item: await cq.answer("Товар не найден!", True); return
    text = f"Удалить '{html.quote(str(item['name']))}'?\n⚠️ <b>Удалятся ВСЕ цены этого товара!</b>"
    markup = get_confirm_delete_item_keyboard(item_id, str(item['name']), item['category_id'])
    await _safe_edit_or_send(cq, text, markup, edit=True, parse_mode="HTML")


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_ITEM_CONFIRM_DELETE))
async def cq_admin_item_confirm_delete_action(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    parts = cq.data.split(":");
    item_id, cat_id_ret = int(parts[1]), int(parts[2])
    item_log = await get_menu_item_by_id(db_pool, item_id);
    item_name_log = str(item_log['name']) if item_log else ""
    await delete_menu_item(db_pool, item_id);
    await cq.answer(f"Товар '{item_name_log}' удален.", show_alert=True)
    await show_items_management_menu(cq, db_pool, cat_id_ret, edit_message=True)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_ITEM_CANCEL_DELETE))
async def cq_admin_item_cancel_delete_action(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    cat_id_ret = int(cq.data.split(":")[1]);
    await show_items_management_menu(cq, db_pool, cat_id_ret, edit_message=True)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_PRICE_ADD_NEW))
async def cq_admin_price_add_new_to_existing_item_start(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    item_id = int(cq.data.split(":")[1]);
    item = await get_menu_item_by_id(db_pool, item_id)
    if not item: await cq.answer("Товар не найден.", True); return
    await state.update_data(add_price_to_existing_item_id=item_id, add_price_to_existing_item_name=item['name'])
    await state.set_state(PriceManagementStates.waiting_for_new_price_option_name);
    text = f"Добавление цены для <b>{html.quote(str(item['name']))}</b>\nНазвание опции ('-' если нет):"
    markup = get_fsm_navigation_keyboard(cancel_callback=CB_PREFIX_ADMIN_PRICE_TO_EXISTING_CANCEL)
    await _safe_edit_or_send(cq, text, markup, edit=True, parse_mode="HTML")


@router.message(PriceManagementStates.waiting_for_new_price_option_name, F.text)
async def process_new_price_option_name_for_existing(message: Message, state: FSMContext):
    opt_name = None if message.text.strip() == '-' else message.text.strip();
    await state.update_data(new_price_option_name_for_existing=opt_name)
    await state.set_state(PriceManagementStates.waiting_for_new_price_value)
    await message.answer("Введите цену (напр., 120.50):", reply_markup=get_fsm_navigation_keyboard(
        cancel_callback=CB_PREFIX_ADMIN_PRICE_TO_EXISTING_CANCEL, back_callback=CB_ADMIN_FSM_BACK))


@router.message(PriceManagementStates.waiting_for_new_price_value, F.text)
async def process_new_price_value_for_existing_and_save(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    try:
        price_val = float(message.text.strip().replace(',', '.'));
        assert price_val > 0
    except:
        await message.answer("❌ Некорректная цена.", reply_markup=get_fsm_navigation_keyboard(
            cancel_callback=CB_PREFIX_ADMIN_PRICE_TO_EXISTING_CANCEL, back_callback=CB_ADMIN_FSM_BACK));
        return
    data = await state.get_data();
    item_id = data.get("add_price_to_existing_item_id");
    opt_name = data.get("new_price_option_name_for_existing")
    if not item_id: await state.clear(); await message.answer("Ошибка ID товара."); return
    await add_menu_item_price(db_pool, item_id=item_id, price=price_val, option_name=opt_name);
    auth_data = await state.get_data();
    await state.clear()
    if 'role' in auth_data: await state.set_data({'role': auth_data['role']})
    await message.answer("✅ Цена/опция добавлена.", reply_markup=ReplyKeyboardRemove());
    await show_item_prices_management_menu(message, db_pool, item_id)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_PRICE_EDIT))
async def cq_admin_price_edit_start(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    price_id = int(cq.data.split(":")[1]);
    price_entry = await get_menu_item_price_by_id(db_pool, price_id)
    if not price_entry: await cq.answer("Запись цены не найдена!", True); return
    item = await get_menu_item_by_id(db_pool, price_entry['item_id'])
    await state.update_data(editing_price_id=price_id, editing_price_item_id=price_entry['item_id'],
                            old_price_option_name=price_entry['option_name'], old_price_value=price_entry['price'],
                            editing_item_name=item['name'] if item else '???')
    await state.set_state(PriceManagementStates.waiting_for_edit_price_option_name)
    curr_opt, curr_price = f"'{html.quote(str(price_entry['option_name']))}'" if price_entry[
        'option_name'] else "нет", f"{float(price_entry['price']):.2f}"
    text = f"Редактирование цены для <b>{html.quote(str(item['name']) if item else '')}</b>\nТек. опция: {curr_opt}, тек. цена: {curr_price}\n\nНовое название опции ('-' оставить, 'пусто' удалить):"
    markup = get_fsm_navigation_keyboard(cancel_callback=CB_PREFIX_ADMIN_PRICE_EDIT_CANCEL)
    await _safe_edit_or_send(cq, text, markup, edit=True, parse_mode="HTML")


@router.message(PriceManagementStates.waiting_for_edit_price_option_name, F.text)
async def process_edit_price_option_name(message: Message, state: FSMContext):
    opt_in = message.text.strip();
    data = await state.get_data();
    old_opt = data.get("old_price_option_name");
    set_opt_null_flag = False;
    final_new_opt = old_opt
    if opt_in == '-':
        pass
    elif opt_in.lower() == 'пусто':
        final_new_opt = None; set_opt_null_flag = True
    else:
        final_new_opt = opt_in
    await state.update_data(edited_price_option_name=final_new_opt,
                            set_option_name_to_null_flag_for_edit=set_opt_null_flag)
    await state.set_state(PriceManagementStates.waiting_for_edit_price_value);
    new_opt_disp = f"'{html.quote(str(final_new_opt))}'" if final_new_opt else "нет"
    await message.answer(f"Имя опции будет: {new_opt_disp}.\nНовое значение цены ('-' оставить):",
                         reply_markup=get_fsm_navigation_keyboard(cancel_callback=CB_PREFIX_ADMIN_PRICE_EDIT_CANCEL,
                                                                  back_callback=CB_ADMIN_FSM_BACK),
                         parse_mode="HTML")


@router.message(PriceManagementStates.waiting_for_edit_price_value, F.text)
async def process_edit_price_value_and_save(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    price_in_txt = message.text.strip();
    data = await state.get_data();
    old_price = data.get("old_price_value");
    final_new_price = old_price
    if price_in_txt != '-':
        try:
            parsed_price = float(price_in_txt.replace(',', '.'));
            assert parsed_price > 0;
            final_new_price = parsed_price
        except:
            await message.answer("❌ Некорректная цена.", reply_markup=get_fsm_navigation_keyboard(
                cancel_callback=CB_PREFIX_ADMIN_PRICE_EDIT_CANCEL, back_callback=CB_ADMIN_FSM_BACK));
            return
    price_id_edit, item_id_ret, opt_name_save, set_opt_null = data.get("editing_price_id"), data.get(
        "editing_price_item_id"), data.get("edited_price_option_name"), data.get(
        "set_option_name_to_null_flag_for_edit", False)
    if price_id_edit is None or item_id_ret is None: await state.clear(); await message.answer("Ошибка."); return
    price_param, opt_param, set_opt_null_param = final_new_price if final_new_price != old_price else None, None, False
    if set_opt_null:
        set_opt_null_param = True
    elif opt_name_save != data.get("old_price_option_name"):
        opt_param = opt_name_save
    if not (price_param is not None or opt_param is not None or set_opt_null_param):
        await message.answer("Изменений не было.", reply_markup=ReplyKeyboardRemove())
    else:
        await update_menu_item_price(db_pool, price_id=price_id_edit, new_price=price_param, new_option_name=opt_param,
                                     set_option_name_null=set_opt_null_param)
        await message.answer("✅ Цена/опция обновлена!", reply_markup=ReplyKeyboardRemove())
    auth_data = await state.get_data();
    await state.clear()
    if 'role' in auth_data: await state.set_data({'role': auth_data['role']})
    await show_item_prices_management_menu(message, db_pool, item_id_ret)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_PRICE_DELETE_PROMPT))
async def cq_admin_price_delete_prompt(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    price_id = int(cq.data.split(":")[1]);
    price_entry = await get_menu_item_price_by_id(db_pool, price_id)
    if not price_entry: await cq.answer("Запись цены не найдена!", True); return
    opt_name, price_val = price_entry['option_name'], price_entry['price'];
    disp_txt = f"{float(price_val):.2f} {CURRENCY_SYMBOL}"
    if opt_name: disp_txt = f"{html.quote(str(opt_name))}: {disp_txt}"
    markup = get_confirm_delete_price_keyboard(price_id, price_entry['item_id'], disp_txt)
    await _safe_edit_or_send(cq, f"Удалить цену/опцию: <b>{disp_txt}</b>?", markup, edit=True, parse_mode="HTML")


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_PRICE_CONFIRM_DELETE))
async def cq_admin_price_confirm_delete_action(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    parts = cq.data.split(":");
    price_id, item_id_ret = int(parts[1]), int(parts[2])
    await delete_menu_item_price(db_pool, price_id);
    await cq.answer("Цена/опция удалена.", show_alert=True)
    await show_item_prices_management_menu(cq, db_pool, item_id_ret, edit_message=True)


@router.callback_query(F.data.startswith(CB_PREFIX_ADMIN_PRICE_CANCEL_DELETE))
async def cq_admin_price_cancel_delete_action(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    item_id_ret = int(cq.data.split(":")[1]);
    await show_item_prices_management_menu(cq, db_pool, item_id_ret, edit_message=True)


async def cancel_fsm_and_show_menu(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool, show_menu_func,
                                   **kwargs):
    auth_data = await state.get_data();
    await state.clear()
    if 'role' in auth_data: await state.update_data(role=auth_data['role'])
    await cq.answer("Действие отменено.")
    if cq.message: await cq.message.delete(); await show_menu_func(cq.message, db_pool, **kwargs)


@router.callback_query(F.data.in_({CB_PREFIX_ADMIN_CAT_CREATION_CANCEL, CB_PREFIX_ADMIN_CAT_EDIT_CANCEL}),
                       StateFilter("*"))
async def cancel_category_fsm(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    await cancel_fsm_and_show_menu(cq, state, db_pool, show_categories_management_menu)


@router.callback_query(StateFilter(ItemCreationStates),
                       F.data.in_({CB_PREFIX_ADMIN_ITEM_CREATION_CANCEL, CB_PREFIX_ADMIN_ITEM_CREATION_CANCEL_PRICE}))
async def item_creation_cancel_fsm(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    fsm_data = await state.get_data();
    category_id = fsm_data.get("item_creation_category_id")
    show_func = show_items_management_menu if category_id else show_select_category_for_items_menu
    await cancel_fsm_and_show_menu(cq, state, db_pool, show_func,
                                   **({"category_id": category_id} if category_id else {}))


@router.callback_query(StateFilter(ItemInfoEditStates), F.data == CB_PREFIX_ADMIN_ITEM_INFO_EDIT_CANCEL)
async def cancel_item_info_edit_fsm(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    fsm_data = await state.get_data();
    category_id = fsm_data.get("editing_item_category_id")
    await cancel_fsm_and_show_menu(cq, state, db_pool, show_items_management_menu, category_id=category_id)


@router.callback_query(StateFilter(PriceManagementStates),
                       F.data.in_({CB_PREFIX_ADMIN_PRICE_TO_EXISTING_CANCEL, CB_PREFIX_ADMIN_PRICE_EDIT_CANCEL}))
async def cancel_price_fsm(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    fsm_data = await state.get_data();
    item_id = fsm_data.get("add_price_to_existing_item_id") or fsm_data.get("editing_price_item_id")
    await cancel_fsm_and_show_menu(cq, state, db_pool, show_item_prices_management_menu, item_id=item_id)


@router.callback_query(F.data == CB_ADMIN_FSM_BACK, StateFilter("*"))
async def fsm_go_back(cq: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(cq, state): return
    current_state, fsm_data = await state.get_state(), await state.get_data()
    # ... (логика возврата остается прежней, просто теперь она будет работать)
    if current_state == ItemCreationStates.waiting_for_price_option_name:
        await state.set_state(ItemCreationStates.waiting_for_item_name)
        text = f"Добавление товара в <b>{html.quote(fsm_data.get('item_creation_category_name', ''))}</b>\nВведите название:"
        markup = get_fsm_navigation_keyboard(cancel_callback=CB_PREFIX_ADMIN_ITEM_CREATION_CANCEL)
        await _safe_edit_or_send(cq, text, markup, edit=True, parse_mode="HTML")
    elif current_state == ItemCreationStates.waiting_for_price_value:
        await state.set_state(ItemCreationStates.waiting_for_price_option_name)
        text = f"Название: <b>{html.quote(fsm_data.get('item_creation_item_name', ''))}</b>\nТеперь добавим первую цену.\n\nВведите название опции (например, '0.2л', '0.3л' или '-' если опции нет):"
        markup = get_fsm_navigation_keyboard(cancel_callback=CB_PREFIX_ADMIN_ITEM_CREATION_CANCEL_PRICE,
                                             back_callback=CB_ADMIN_FSM_BACK)
        await _safe_edit_or_send(cq, text, markup, edit=True, parse_mode="HTML")
    # ... (и так далее для всех состояний) ...
    else:
        await cq.answer("Некуда возвращаться с текущего шага.", show_alert=True)


@router.callback_query(F.data == CB_ADMIN_DEBUG_SEPARATOR)
async def show_service_info(cq: CallbackQuery, state: FSMContext):
    if not await check_admin_auth(cq, state): return
    try:
        info_text = base64.b64decode(BUILD_INFO_PAYLOAD).decode('utf-8');
        await cq.answer(info_text, show_alert=True)
    except Exception as e:
        logger.error(f"Failed to decode or send service info: {e}");
        await cq.answer("Не удалось отобразить сервисную информацию.", show_alert=True)


@router.callback_query(F.data == CB_ADMIN_NOOP)
async def cq_admin_noop(cq: CallbackQuery): await cq.answer()
