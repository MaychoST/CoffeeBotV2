# utils.py
import logging
from aiogram import Bot, html
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from constants import CURRENCY_SYMBOL
from database import get_orders_by_status, get_order_items, get_order_by_id
from keyboards import (
    get_active_orders_inline_keyboard,
    get_edit_order_actions_keyboard,
    get_admin_menu_keyboard,
    get_barista_menu_keyboard
)

logger = logging.getLogger(__name__)


async def _display_active_orders_list(
        bot_instance: Bot, chat_id: int, user_role: str | None,
        message_to_edit_id: int | None = None, show_main_menu_if_no_orders: bool = True
):
    logger.info(
        f"Displaying active orders for chat_id: {chat_id}, role: {user_role}. Edit msg_id: {message_to_edit_id}")
    menu_kb = get_admin_menu_keyboard() if user_role == "admin" else (
        get_barista_menu_keyboard() if user_role == "barista" else None)
    if not menu_kb: logger.warning(f"Could not determine menu keyboard for role: {user_role} in chat_id: {chat_id}")

    active_orders_db = await get_orders_by_status('new')
    if not active_orders_db:
        no_orders_text = "Активных заказов нет. Можно отдохнуть! 🍹"
        try:
            if message_to_edit_id:
                await bot_instance.edit_message_text(chat_id=chat_id, message_id=message_to_edit_id,
                                                     text=no_orders_text, reply_markup=None)
            else:
                await bot_instance.send_message(chat_id, no_orders_text, reply_markup=None)
        except TelegramBadRequest as e:
            logger.warning(f"Failed to edit/send 'no active orders' message: {e}.")
            if message_to_edit_id: await bot_instance.send_message(chat_id, no_orders_text, reply_markup=None)
        if show_main_menu_if_no_orders and menu_kb:
            await bot_instance.send_message(chat_id, "Что бы вы хотели сделать дальше?", reply_markup=menu_kb)
        return

    response_text = "<b>Активные заказы (статус 'new'):</b>\n\n"
    orders_for_keyboard = []
    for order_data in active_orders_db:
        order_id_db = order_data['id']
        # --- ИЗМЕНЕНИЕ: Используем daily_sequence_number ---
        daily_num = order_data.get('daily_sequence_number', order_id_db)
        total_amount = order_data['total_amount']
        created_at_formatted = order_data['created_at'].strftime('%H:%M (%d.%m.%Y)')
        items_in_order = await get_order_items(order_id_db)

        response_text += f"<b>Заказ #{daily_num}</b> (от {created_at_formatted})\n"
        response_text += f"Сумма: {total_amount:.2f} {CURRENCY_SYMBOL}\n"
        response_text += "Состав:\n"
        if items_in_order:
            for item in items_in_order:
                response_text += f"  - {html.quote(item['item_name'])} ({item['chosen_price']:.2f} {CURRENCY_SYMBOL}) x {item['quantity']}\n"
        else:
            response_text += "  - (нет информации о позициях)\n"
        response_text += "--------------------\n"
        orders_for_keyboard.append({'id': order_id_db, 'daily_num': daily_num})  # Передаем и дневной номер

    # Используем новый get_active_orders_inline_keyboard
    reply_markup_val = get_active_orders_inline_keyboard(orders_for_keyboard)

    try:
        if message_to_edit_id:
            await bot_instance.edit_message_text(chat_id=chat_id, message_id=message_to_edit_id, text=response_text,
                                                 reply_markup=reply_markup_val, parse_mode="HTML")
            if menu_kb: await bot_instance.send_message(chat_id, "Список активных заказов обновлен.",
                                                        reply_markup=menu_kb)
        else:
            await bot_instance.send_message(chat_id, response_text, reply_markup=reply_markup_val, parse_mode="HTML")
    except TelegramBadRequest as e:
        logger.warning(f"Failed to edit/send active orders list: {e}. Sending new message.")
        if message_to_edit_id:
            await bot_instance.send_message(chat_id, response_text, reply_markup=reply_markup_val, parse_mode="HTML")
            if menu_kb: await bot_instance.send_message(chat_id, "Список обновлен.", reply_markup=menu_kb)


async def _display_edit_order_interface(
        target_message_or_bot: Message | Bot, order_id: int,
        chat_id_for_new: int | None = None, custom_text_prefix: str | None = None
):
    logger.info(f"Displaying/Refreshing edit interface for order ID: {order_id}")
    actual_bot_instance = target_message_or_bot if isinstance(target_message_or_bot, Bot) else target_message_or_bot.bot
    message_to_edit = target_message_or_bot if isinstance(target_message_or_bot, Message) else None
    target_chat_id = chat_id_for_new or (message_to_edit.chat.id if message_to_edit else None)
    if not target_chat_id: logger.error(
        f"Cannot display edit order interface for order {order_id}: no target_chat_id."); return

    order_data = await get_order_by_id(order_id)
    if not order_data or order_data['status'] != 'new':
        error_text = f"Заказ ID: {order_id} больше не существует или не может быть отредактирован."
        if message_to_edit:
            try:
                await message_to_edit.edit_text(error_text, reply_markup=None)
            except TelegramBadRequest:
                pass
        else:
            await actual_bot_instance.send_message(target_chat_id, error_text)
        return

    order_items = await get_order_items(order_id)
    # --- ИЗМЕНЕНИЕ: Используем daily_sequence_number ---
    daily_num = order_data.get('daily_sequence_number', order_id)
    response_text = f"{custom_text_prefix}\n\n" if custom_text_prefix else ""
    response_text += f"✏️ <b>Редактирование Заказа #{daily_num}</b>\nСумма: {order_data['total_amount']:.2f} {CURRENCY_SYMBOL}\n\n"
    if order_items:
        response_text += "<b>Состав заказа:</b>\n"
        for i, item_row in enumerate(order_items, 1):
            response_text += f"{i}. {html.quote(item_row['item_name'])} ({item_row['chosen_price']:.2f} {CURRENCY_SYMBOL}) x {item_row['quantity']}\n"
    else:
        response_text += "Заказ стал пустым (все позиции удалены).\n"
    response_text += "\nВыберите действие:"
    reply_markup_val = get_edit_order_actions_keyboard(order_id)

    if message_to_edit:
        try:
            await message_to_edit.edit_text(response_text, reply_markup=reply_markup_val, parse_mode="HTML")
        except TelegramBadRequest:
            await actual_bot_instance.send_message(target_chat_id, response_text, reply_markup=reply_markup_val,
                                                   parse_mode="HTML")
    else:
        await actual_bot_instance.send_message(target_chat_id, response_text, reply_markup=reply_markup_val,
                                               parse_mode="HTML")
