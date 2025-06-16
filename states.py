# states.py
from aiogram.fsm.state import State, StatesGroup


class ItemSelectionProcessStates(StatesGroup):
    choosing_category = State()
    choosing_item = State()
    choosing_price_option = State()
    choosing_quantity = State()
    waiting_for_manual_quantity = State()


# --- НОВАЯ ГРУППА СОСТОЯНИЙ ---
class AdminNavigationStates(StatesGroup):
    in_menu_management = State()  # Состояние, когда пользователь находится в меню "Управление меню"


class CategoryManagementStates(StatesGroup):
    waiting_for_new_category_name = State()
    waiting_for_edit_category_name = State()


class ItemCreationStates(StatesGroup):
    waiting_for_item_name = State()
    waiting_for_item_description = State()
    waiting_for_price_option_name = State()
    waiting_for_price_value = State()


class ItemInfoEditStates(StatesGroup):
    waiting_for_edit_item_name = State()
    waiting_for_edit_item_description = State()


class PriceManagementStates(StatesGroup):
    waiting_for_new_price_option_name = State()
    waiting_for_new_price_value = State()
    waiting_for_edit_price_option_name = State()
    waiting_for_edit_price_value = State()


class ReportStates(StatesGroup):
    waiting_for_start_date = State()
    waiting_for_end_date = State()


# --- НОВЫЙ КЛАСС СОСТОЯНИЙ ---
class BugReportStates(StatesGroup):
    waiting_for_report_text = State()
