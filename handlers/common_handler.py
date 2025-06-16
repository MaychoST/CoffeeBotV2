# Имя файла: handlers/common_handler.py (ФИНАЛЬНАЯ ВЕРСИЯ)

import logging
import asyncpg
from aiogram import Router, F, types
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery

from keyboards import get_auth_keyboard, get_cancel_keyboard, get_admin_menu_keyboard, get_barista_menu_keyboard
from constants import GENERAL_CANCEL_TEXT, LOGOUT_BUTTON_TEXT, SCREEN_CLEAR_DIVIDER
from states import BugReportStates
from database import save_bug_report

router = Router()
logger = logging.getLogger(__name__)


async def check_auth(target: Message | CallbackQuery, state: FSMContext) -> str | None:
    data = await state.get_data()
    role = data.get('role')
    if role not in ['admin', 'barista']:
        if isinstance(target, Message):
            await target.answer("Эта функция доступна только авторизованным пользователям.")
        return None
    return role


@router.message(CommandStart(), StateFilter("*"))
async def handle_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 <b>Добро пожаловать в CoffeeBotV2!</b>\n\n"
        "Пожалуйста, авторизуйтесь, отправив ваш пароль.",
        reply_markup=get_auth_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_role = user_data.get('role')
    help_text = "👋 **Справка по боту CoffeeBotV2**\n\n"
    if user_role == 'admin':
        help_text += ("Вы вошли как **Администратор**.\n\n"
                      "**Основные команды:**\n"
                      "`/start` - перезапустить бота, вернуться в главное меню.\n"
                      "`/logout` - выйти из системы.\n"
                      "`/bug` - сообщить о технической проблеме.\n\n"
                      "**Возможности админ-панели:**\n"
                      "• **Управление заказами:** Создание, редактирование и просмотр текущих заказов.\n"
                      "• **Управление меню:** Добавление, изменение и удаление позиций и категорий в меню кофейни.\n"
                      "• **Отчеты:** Просмотр отчетов о продажах.\n\n"
                      "Для доступа к этим функциям вернитесь в главное меню.")
    elif user_role == 'barista':
        help_text += ("Вы вошли как **Бариста**.\n\n"
                      "**Основные команды:**\n"
                      "`/start` - перезапустить бота, вернуться в главное меню.\n"
                      "`/logout` - выйти из системы.\n"
                      "`/bug` - сообщить о технической проблеме.\n\n"
                      "**Ваши возможности:**\n"
                      "• **Прием заказов:** Используйте кнопки в главном меню для быстрого создания и редактирования заказов.\n"
                      "• **Нумерация:** Заказы нумеруются автоматически в течение дня (Заказ #1, Заказ #2 и т.д.).\n\n"
                      "Если у вас возникли сложности, обратитесь к администратору или воспользуйтесь командой `/bug`.")
    else:
        help_text += ("Добро пожаловать!\n"
                      "Это бот для персонала кофейни. Чтобы начать работу, вам необходимо авторизоваться.\n\n"
                      "Пожалуйста, введите ваш рабочий пароль.")
    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("logout"), StateFilter("*"))
@router.message(F.text.casefold() == LOGOUT_BUTTON_TEXT.lower(), StateFilter("*"))
async def handle_logout(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(f"{SCREEN_CLEAR_DIVIDER}Вы успешно вышли из системы.", reply_markup=ReplyKeyboardRemove())
    await message.answer("Для продолжения работы, пожалуйста, авторизуйтесь.", reply_markup=get_auth_keyboard())


@router.message(Command("bug"), StateFilter("*"))
async def bug_report_start(message: Message, state: FSMContext):
    if not await check_auth(message, state):
        return
    await state.set_state(BugReportStates.waiting_for_report_text)
    await message.answer("🐞 <b>Сообщить об ошибке</b>\n\nПожалуйста, опишите проблему...",
                         reply_markup=get_cancel_keyboard())


@router.message(BugReportStates.waiting_for_report_text, F.text)
async def bug_report_process_text(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    data = await state.get_data()
    user_role = data.get('role')
    response_text = ""
    if message.text == GENERAL_CANCEL_TEXT:
        response_text = "Отправка отчета отменена."
    else:
        # <<< ИЗМЕНЕНИЕ: Передаем db_pool
        success = await save_bug_report(db_pool, message.from_user.id, user_role, message.text)
        if success:
            response_text = "✅ Спасибо! Ваш отчет об ошибке отправлен."
        else:
            response_text = "❌ Не удалось отправить отчет. Попробуйте позже."
    await state.clear()
    if user_role:
        await state.set_data({'role': user_role})
    await message.answer(response_text, reply_markup=ReplyKeyboardRemove())
    if user_role == 'admin':
        await message.answer("Возвращаю в главное меню администратора.", reply_markup=get_admin_menu_keyboard())
    elif user_role == 'barista':
        await message.answer("Возвращаю в главное меню бариста.", reply_markup=get_barista_menu_keyboard())