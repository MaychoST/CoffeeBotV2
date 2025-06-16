# keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from constants import *


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=CREATE_ORDER_TEXT))
    builder.row(KeyboardButton(text=VIEW_ACTIVE_ORDERS_TEXT), KeyboardButton(text=REPORTS_MENU_TEXT))
    builder.row(KeyboardButton(text=ADMIN_MENU_MANAGEMENT_TEXT))
    builder.row(KeyboardButton(text=LOGOUT_BUTTON_TEXT))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_barista_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=CREATE_ORDER_TEXT))
    builder.row(KeyboardButton(text=VIEW_ACTIVE_ORDERS_TEXT))
    builder.row(KeyboardButton(text=LOGOUT_BUTTON_TEXT))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_auth_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder();
    builder.button(text=AUTH_BUTTON_TEXT)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_categories_keyboard(categories: list[str]) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for category in categories: builder.button(text=category)
    builder.adjust(2);
    builder.row(KeyboardButton(text=CANCEL_ORDER_CREATION_TEXT))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_items_keyboard(items_with_price_info: list[str], category_name: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for item_str in items_with_price_info: builder.button(text=item_str)
    builder.adjust(1);
    builder.row(KeyboardButton(text=f"🔙 К категориям ({category_name})"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_price_options_keyboard(price_options: list, item_name: str, category_name: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for price in price_options: builder.button(text=f"{float(price):.2f} {CURRENCY_SYMBOL}")
    builder.adjust(3);
    builder.row(KeyboardButton(text=f"🔙 К товарам ({category_name})"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_order_actions_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=VIEW_CURRENT_ORDER_TEXT))
    builder.row(KeyboardButton(text=ADD_MORE_TO_ORDER_TEXT))
    builder.row(KeyboardButton(text=COMPLETE_AND_SAVE_ORDER_TEXT))
    builder.row(KeyboardButton(text=CANCEL_IN_PROGRESS_ORDER_TEXT))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_cancel_keyboard(text: str = GENERAL_CANCEL_TEXT) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder();
    builder.button(text=text)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# --- ИЗМЕНЕНИЕ: Функция теперь принимает `daily_num` ---
def get_active_orders_inline_keyboard(active_orders_data: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if active_orders_data:
        for order_info in active_orders_data:
            order_id = order_info['id']
            daily_num = order_info.get('daily_num', order_id)  # Фоллбэк на системный ID
            buttons_for_order = [
                InlineKeyboardButton(text=f"Выполнен ✅ (Заказ #{daily_num})",
                                     callback_data=f"{CB_PREFIX_COMPLETE_ORDER}{order_id}"),
                InlineKeyboardButton(text=f"✏️ Редакт. (Заказ #{daily_num})",
                                     callback_data=f"{CB_PREFIX_EDIT_ORDER}{order_id}")
            ]
            builder.row(*buttons_for_order)
    return builder.as_markup()


def get_edit_order_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Удалить позицию", callback_data=f"{CB_PREFIX_EDIT_ORDER_DELETE_PROMPT}{order_id}")
    builder.button(text="➕ Добавить позицию", callback_data=f"{CB_PREFIX_EDIT_ORDER_ADD_ITEM_START}{order_id}")
    builder.adjust(1);
    builder.row(InlineKeyboardButton(text="Готово (к списку заказов)",
                                     callback_data=f"{CB_PREFIX_EDIT_ORDER_FINISH}{order_id}"))
    return builder.as_markup()


def get_admin_menu_management_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=MANAGE_CATEGORIES_TEXT))
    builder.row(KeyboardButton(text=MANAGE_ITEMS_TEXT))
    builder.row(KeyboardButton(text=BACK_TO_ADMIN_MAIN_MENU_TEXT))
    return builder.as_markup(resize_keyboard=True)


def get_admin_categories_management_keyboard(categories: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder();
    builder.row(InlineKeyboardButton(text="✨ Добавить новую категорию", callback_data=CB_PREFIX_ADMIN_CAT_ADD_NEW))
    if categories:
        builder.row(InlineKeyboardButton(text="--- Категории ---", callback_data=CB_ADMIN_DEBUG_SEPARATOR))
        for category in categories:
            cat_id, name, active = category['id'], category['name'], category['is_active']
            status, action_txt = ("✅", "Скрыть") if active else ("❌", "Показать")
            builder.row(
                InlineKeyboardButton(text=f"{status} {name}", callback_data=f"{CB_PREFIX_ADMIN_CAT_VIEW}{cat_id}"))
            builder.row(
                InlineKeyboardButton(text="✏️ Ред.", callback_data=f"{CB_PREFIX_ADMIN_CAT_EDIT}{cat_id}"),
                InlineKeyboardButton(text=action_txt, callback_data=f"{CB_PREFIX_ADMIN_CAT_TOGGLE_ACTIVE}{cat_id}"),
                InlineKeyboardButton(text="🗑️ Удал.", callback_data=f"{CB_PREFIX_ADMIN_CAT_DELETE_PROMPT}{cat_id}")
            );
            builder.row(InlineKeyboardButton(text="---", callback_data=CB_ADMIN_NOOP))
    builder.row(InlineKeyboardButton(text="🔙 Назад к управлению меню", callback_data=CB_PREFIX_ADMIN_MENU_MANAGE_BACK))
    return builder.as_markup()


def get_confirm_delete_category_keyboard(category_id: int, category_name: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"🗑️ Да, удалить '{category_name}'",
                   callback_data=f"{CB_PREFIX_ADMIN_CAT_CONFIRM_DELETE}{category_id}")
    builder.button(text="🚫 Отмена", callback_data=CB_PREFIX_ADMIN_CAT_CANCEL_DELETE);
    builder.adjust(1)
    return builder.as_markup()


def get_fsm_navigation_keyboard(cancel_callback: str, back_callback: str | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder();
    buttons = []
    if back_callback: buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback))
    buttons.append(InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_callback));
    builder.row(*buttons)
    return builder.as_markup()


def get_admin_select_category_for_items_keyboard(categories: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder();
    builder.row(InlineKeyboardButton(text="--- Выберите категорию для товаров ---", callback_data=CB_ADMIN_NOOP))
    if categories:
        for category in categories: builder.button(text=category['name'],
                                                   callback_data=f"{CB_PREFIX_ADMIN_ITEM_MANAGE_CAT_SELECT}{category['id']}")
        builder.adjust(2)
    else:
        builder.row(InlineKeyboardButton(text="Нет категорий для выбора", callback_data=CB_ADMIN_NOOP))
    builder.row(InlineKeyboardButton(text="🔙 Назад к управлению меню", callback_data=CB_PREFIX_ADMIN_MENU_MANAGE_BACK))
    return builder.as_markup()


def get_admin_items_management_keyboard(items: list, category_id: int, category_name: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder();
    builder.row(InlineKeyboardButton(text=f"✨ Добавить товар в '{category_name}'",
                                     callback_data=f"{CB_PREFIX_ADMIN_ITEM_ADD_NEW}{category_id}"))
    if items:
        builder.row(InlineKeyboardButton(text=f"--- Товары в '{category_name}' ---", callback_data=CB_ADMIN_NOOP))
        for item in items:
            item_id, name, active = item['id'], item['name'], item['is_active']
            status, action_txt = ("✅", "Скрыть") if active else ("❌", "Показать")
            builder.row(InlineKeyboardButton(text=f"{status} {name}",
                                             callback_data=f"{CB_PREFIX_ADMIN_ITEM_MANAGE_PRICES}{item_id}"))
            builder.row(
                InlineKeyboardButton(text="✏️ Ред. инфо", callback_data=f"{CB_PREFIX_ADMIN_ITEM_EDIT_INFO}{item_id}"),
                InlineKeyboardButton(text=action_txt, callback_data=f"{CB_PREFIX_ADMIN_ITEM_TOGGLE_ACTIVE}{item_id}"),
                InlineKeyboardButton(text="🗑️ Удал.", callback_data=f"{CB_PREFIX_ADMIN_ITEM_DELETE_PROMPT}{item_id}")
            );
            builder.row(InlineKeyboardButton(text="—" * 15, callback_data=CB_ADMIN_NOOP))
    else:
        builder.row(InlineKeyboardButton(text="В этой категории пока нет товаров.", callback_data=CB_ADMIN_NOOP))
    builder.row(InlineKeyboardButton(text="🔙 К выбору категории (для товаров)",
                                     callback_data=CB_PREFIX_ADMIN_ITEM_CAT_SELECT_BACK))
    return builder.as_markup()


def get_confirm_delete_item_keyboard(item_id: int, item_name: str, category_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"🗑️ Да, удалить '{item_name}'",
                   callback_data=f"{CB_PREFIX_ADMIN_ITEM_CONFIRM_DELETE}{item_id}:{category_id}")
    builder.button(text="🚫 Отмена", callback_data=f"{CB_PREFIX_ADMIN_ITEM_CANCEL_DELETE}{category_id}");
    builder.adjust(1)
    return builder.as_markup()


def get_admin_item_prices_management_keyboard(prices: list, item_id: int, item_name: str,
                                              category_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder();
    builder.row(InlineKeyboardButton(text=f"Управление ценами для: '{item_name}'", callback_data=CB_ADMIN_NOOP))
    builder.row(
        InlineKeyboardButton(text="✨ Добавить цену/опцию", callback_data=f"{CB_PREFIX_ADMIN_PRICE_ADD_NEW}{item_id}"))
    builder.row(InlineKeyboardButton(text="--- Текущие цены/опции ---", callback_data=CB_ADMIN_NOOP))
    if prices:
        for price_entry in prices:
            price_id, option_name, price_value = price_entry['id'], price_entry['option_name'], price_entry['price']
            display_text = f"{float(price_value):.2f} {CURRENCY_SYMBOL}";
            if option_name: display_text = f"{option_name}: {display_text}"
            builder.row(
                InlineKeyboardButton(text=display_text, callback_data=f"{CB_PREFIX_ADMIN_PRICE_VIEW}{price_id}"))
            builder.row(
                InlineKeyboardButton(text="✏️ Ред.", callback_data=f"{CB_PREFIX_ADMIN_PRICE_EDIT}{price_id}"),
                InlineKeyboardButton(text="🗑️ Удал.", callback_data=f"{CB_PREFIX_ADMIN_PRICE_DELETE_PROMPT}{price_id}")
            );
            builder.row(InlineKeyboardButton(text="---", callback_data=CB_ADMIN_NOOP))
    else:
        builder.row(InlineKeyboardButton(text="Для этого товара пока нет цен/опций.", callback_data=CB_ADMIN_NOOP))
    builder.row(InlineKeyboardButton(text="🔙 К товарам категории",
                                     callback_data=f"{CB_PREFIX_ADMIN_ITEM_MANAGE_CAT_SELECT}{category_id}"))
    return builder.as_markup()


def get_confirm_delete_price_keyboard(price_id: int, item_id: int, display_text: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"🗑️ Да, удалить '{display_text}'",
                   callback_data=f"{CB_PREFIX_ADMIN_PRICE_CONFIRM_DELETE}{price_id}:{item_id}")
    builder.button(text="🚫 Отмена", callback_data=f"{CB_PREFIX_ADMIN_PRICE_CANCEL_DELETE}{item_id}");
    builder.adjust(1)
    return builder.as_markup()


def get_items_to_delete_keyboard(order_items: list, order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if order_items:
        for i, item_row in enumerate(order_items, 1):
            item_order_item_id, item_name, price, quantity = item_row['id'], item_row['item_name'], item_row[
                'chosen_price'], item_row['quantity']
            button_text = f"{i}. {item_name} ({price:.2f} {CURRENCY_SYMBOL}) x {quantity}"
            builder.button(text=button_text,
                           callback_data=f"{CB_PREFIX_EDIT_ORDER_CONFIRM_DELETE}{item_order_item_id}:{order_id}")
        builder.adjust(1)
    builder.row(InlineKeyboardButton(text="↩️ Назад к ред. заказа", callback_data=f"{CB_PREFIX_EDIT_ORDER}{order_id}"))
    return builder.as_markup()


def get_reports_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=SALES_TODAY_TEXT));
    builder.row(KeyboardButton(text=SALES_YESTERDAY_TEXT))
    builder.row(KeyboardButton(text=SALES_PERIOD_TEXT));
    builder.row(KeyboardButton(text=BACK_TO_ADMIN_MAIN_MENU_TEXT))
    return builder.as_markup(resize_keyboard=True)


def get_quantity_keyboard(cancel_text: str = "🔙 Отменить") -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for i in range(1, 6): builder.button(text=str(i))
    builder.button(text=OTHER_QUANTITY_TEXT);
    builder.adjust(3, 3);
    builder.row(KeyboardButton(text=cancel_text))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_confirm_add_another_price_keyboard(item_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Да, добавить еще", callback_data=f"{CB_PREFIX_ADMIN_ITEM_CREATION_ADD_ANOTHER_PRICE}{item_id}")
    builder.button(text="Нет, завершить", callback_data=f"{CB_PREFIX_ADMIN_ITEM_CREATION_FINISH}{item_id}");
    builder.adjust(2)
    return builder.as_markup()


def get_manual_input_cancel_keyboard(cancel_text: str = GENERAL_CANCEL_TEXT) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder();
    builder.button(text=cancel_text)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
