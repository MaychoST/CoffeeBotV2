# constants.py

BUILD_INFO_PAYLOAD = "Q29mZmVlQm90VjIK0JLQtdGA0YHQuNGPOiAzLjAgKNCk0LjQvdCw0LspCtCU0LDRgtCwINGB0LHQvtGA0LrQuDogMDkuMDYuMjAyNQoK0KDQsNC30YDQsNCx0L7RgtGH0LjQujogQE1heWNob1NUCg=="
SCREEN_CLEAR_DIVIDER = "\n" * 50
# --- Общие тексты и символы ---
CURRENCY_SYMBOL = "сом"
CB_ADMIN_DEBUG_SEPARATOR = "admin_debug_sep"

# --- Тексты для ReplyKeyboardMarkup кнопок ---
# Start Handler & Auth
AUTH_BUTTON_TEXT = "Авторизация"
LOGOUT_BUTTON_TEXT = "Выйти"

# Main Menu (Admin & Barista)
CREATE_ORDER_TEXT = "Создать заказ"
VIEW_ACTIVE_ORDERS_TEXT = "Посмотреть активные заказы"

# Admin Main Menu Specific
REPORTS_MENU_TEXT = "Отчеты"
ADMIN_MENU_MANAGEMENT_TEXT = "Управление меню"

# Order Handler (действия с собираемым заказом)
VIEW_CURRENT_ORDER_TEXT = "Посмотреть текущий заказ"
ADD_MORE_TO_ORDER_TEXT = "Добавить еще товар"
COMPLETE_AND_SAVE_ORDER_TEXT = "✅ Завершить и оформить заказ"
CANCEL_IN_PROGRESS_ORDER_TEXT = "❌ Отменить заказ"

# Order Handler (навигация в FSM)
CANCEL_ORDER_CREATION_TEXT = "🔙 Отменить заказ"

# Quantity Keyboard
OTHER_QUANTITY_TEXT = "Другое кол-во"

# Admin Menu Management
MANAGE_CATEGORIES_TEXT = "Управление категориями"
MANAGE_ITEMS_TEXT = "Управление товарами"
BACK_TO_ADMIN_MAIN_MENU_TEXT = "🔙 В главное меню админа"

# Report Handler
SALES_TODAY_TEXT = "📊 Заказы за сегодня"
SALES_YESTERDAY_TEXT = "🗓️ Заказы за вчера"
SALES_PERIOD_TEXT = "📅 Заказы за период"

# --- Callback Data Prefixes ---
# Для staff_handler (управление активными заказами)
CB_PREFIX_COMPLETE_ORDER = "complete_order_id:"
CB_PREFIX_EDIT_ORDER = "edit_order_id:"
CB_PREFIX_EDIT_ORDER_DELETE_PROMPT = "editord_del_item_prompt:"
CB_PREFIX_EDIT_ORDER_CONFIRM_DELETE = "editord_confirm_del_item:"
CB_PREFIX_EDIT_ORDER_ADD_ITEM_START = "editord_add_item_start:"
CB_PREFIX_EDIT_ORDER_FINISH = "editord_finish:"

# Для admin_menu_management_handler (категории)
CB_PREFIX_ADMIN_CAT_ADD_NEW = "admin_cat_add_new"
CB_PREFIX_ADMIN_CAT_VIEW = "admin_cat_view:"
CB_PREFIX_ADMIN_CAT_EDIT = "admin_cat_edit:"
CB_PREFIX_ADMIN_CAT_TOGGLE_ACTIVE = "admin_cat_toggle_active:"
CB_PREFIX_ADMIN_CAT_DELETE_PROMPT = "admin_cat_delete:"
CB_PREFIX_ADMIN_CAT_CONFIRM_DELETE = "admin_cat_confirm_delete:"
CB_PREFIX_ADMIN_CAT_CANCEL_DELETE = "admin_cat_cancel_delete"
CB_PREFIX_ADMIN_MENU_MANAGE_BACK = "admin_menu_manage_back"
CB_PREFIX_ADMIN_CAT_CREATION_CANCEL = "admin_cat_creation_cancel"
CB_PREFIX_ADMIN_CAT_EDIT_CANCEL = "admin_cat_edit_cancel"

# Для admin_menu_management_handler (товары)
CB_PREFIX_ADMIN_ITEM_MANAGE_CAT_SELECT = "admin_item_manage_cat_select:"
CB_PREFIX_ADMIN_ITEM_ADD_NEW = "admin_item_add_new:"
CB_PREFIX_ADMIN_ITEM_MANAGE_PRICES = "admin_item_manage_prices:"
CB_PREFIX_ADMIN_ITEM_EDIT_INFO = "admin_item_edit_info:"
CB_PREFIX_ADMIN_ITEM_TOGGLE_ACTIVE = "admin_item_toggle_active:"
CB_PREFIX_ADMIN_ITEM_DELETE_PROMPT = "admin_item_delete:"
CB_PREFIX_ADMIN_ITEM_CONFIRM_DELETE = "admin_item_confirm_delete:"
CB_PREFIX_ADMIN_ITEM_CANCEL_DELETE = "admin_item_cancel_delete:"
CB_PREFIX_ADMIN_ITEM_CAT_SELECT_BACK = "admin_item_cat_select_back"

# Для admin_menu_management_handler (создание товара - FSM)
CB_PREFIX_ADMIN_ITEM_CREATION_CANCEL = "admin_item_creation_cancel"
CB_PREFIX_ADMIN_ITEM_CREATION_CANCEL_PRICE = "admin_item_creation_cancel_price"
CB_PREFIX_ADMIN_ITEM_CREATION_ADD_ANOTHER_PRICE = "admin_item_creation_add_another_price:"
CB_PREFIX_ADMIN_ITEM_CREATION_FINISH = "admin_item_creation_finish:"

# Для admin_menu_management_handler (редактирование инфо о товаре - FSM)
CB_PREFIX_ADMIN_ITEM_INFO_EDIT_CANCEL = "admin_item_info_edit_cancel"

# Для admin_menu_management_handler (цены существующего товара)
CB_PREFIX_ADMIN_PRICE_ADD_NEW = "admin_price_add_new:"
CB_PREFIX_ADMIN_PRICE_VIEW = "admin_price_view:"
CB_PREFIX_ADMIN_PRICE_EDIT = "admin_price_edit:"
CB_PREFIX_ADMIN_PRICE_DELETE_PROMPT = "admin_price_delete:"
CB_PREFIX_ADMIN_PRICE_CONFIRM_DELETE = "admin_price_confirm_delete:"
CB_PREFIX_ADMIN_PRICE_CANCEL_DELETE = "admin_price_cancel_delete:"
CB_PREFIX_ADMIN_PRICE_TO_EXISTING_CANCEL = "admin_price_to_existing_cancel"
CB_PREFIX_ADMIN_PRICE_EDIT_CANCEL = "admin_price_edit_cancel"

# Общие callback_data
CB_ADMIN_NOOP = "admin_noop"
GENERAL_CANCEL_TEXT = "Отмена"

# --- НОВЫЙ КОЛБЭК ДЛЯ НАВИГАЦИИ ---
# Универсальный callback для кнопки "Назад" в FSM
CB_ADMIN_FSM_BACK = "admin_fsm_back"