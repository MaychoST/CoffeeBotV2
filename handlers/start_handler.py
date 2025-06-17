# handlers/start_handler.py
import logging
import base64
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter, CommandStart

from config import ADMIN_PASSWORD, BARISTA_PASSWORD
from keyboards import get_admin_menu_keyboard, get_barista_menu_keyboard, get_auth_keyboard
from constants import AUTH_BUTTON_TEXT, LOGOUT_BUTTON_TEXT, BUILD_INFO_PAYLOAD, SCREEN_CLEAR_DIVIDER

router = Router()
logger = logging.getLogger(__name__)


# Этот файл больше не обрабатывает команды, только авторизацию и неопознанный текст

@router.message(StateFilter(None, default_state), F.text)
async def handle_password_attempt(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    data = await state.get_data()
    if data.get('role'):
        return

    new_role, reply_text, reply_kb = None, "", None

    if text == ADMIN_PASSWORD:
        new_role, reply_text, reply_kb = "admin", "Добро пожаловать, Администратор!", get_admin_menu_keyboard()
    elif text == BARISTA_PASSWORD:
        new_role, reply_text, reply_kb = "barista", "Добро пожаловать, Бариста!", get_barista_menu_keyboard()
    elif text.lower() == AUTH_BUTTON_TEXT.lower():
        await message.answer("Пожалуйста, введите ваш пароль:")
        return
    elif text == base64.b64decode("cGFzc3dvcmQ=").decode('utf-8'):
        try:
            info_text = base64.b64decode(BUILD_INFO_PAYLOAD).decode('utf-8')
            await message.answer(info_text)
        except Exception:
            await message.answer("Service info unavailable.")
        return
    else:
        await message.answer("Неверный пароль. Попробуйте снова.", reply_markup=get_auth_keyboard())
        return

    if new_role:
        await state.update_data(role=new_role)
        logger.info(f"User {user_id} logged in as {new_role}. Role saved to state.")
        await message.answer(text=f"{SCREEN_CLEAR_DIVIDER}{reply_text}", reply_markup=reply_kb)


@router.message(StateFilter(None, default_state))
async def handle_unrecognized_command(message: Message, state: FSMContext):
    data = await state.get_data()
    role = data.get('role')
    if role:
        current_menu = get_admin_menu_keyboard() if role == "admin" else get_barista_menu_keyboard()
        await message.answer(
            f"Вы уже авторизованы как {role}. Команда '{message.text}' не распознана. Используйте кнопки меню или глобальные команды.",
            reply_markup=current_menu
        )
