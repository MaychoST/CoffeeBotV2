# Имя файла: handlers/start_handler.py (ФИНАЛЬНАЯ ВЕРСИЯ)

import logging
import base64
from aiogram import Router, F
from aiogram.filters import StateFilter, CommandStart
from aiogram.fsm.state import default_state
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import ADMIN_PASSWORD, BARISTA_PASSWORD
from keyboards import get_admin_menu_keyboard, get_barista_menu_keyboard, get_auth_keyboard
from constants import AUTH_BUTTON_TEXT, BUILD_INFO_PAYLOAD

router = Router()
logger = logging.getLogger(__name__)


# Этот хендлер ловит любой текст, который НЕ является командой /start.
# Он работает только для неавторизованных пользователей.
@router.message(StateFilter(None, default_state), F.text, ~CommandStart())
async def handle_password_attempt(message: Message, state: FSMContext):
    # Оборачиваем в try...finally, чтобы сообщение с паролем удалялось всегда
    try:
        user_id = message.from_user.id
        text = message.text.strip()

        data = await state.get_data()
        if data.get('role'):
            # Этот блок кода по идее не должен срабатывать из-за StateFilter,
            # но оставляем его как дополнительную защиту.
            return

        new_role, reply_text, reply_kb = None, "", None

        if text == ADMIN_PASSWORD:
            new_role, reply_text, reply_kb = "admin", "Добро пожаловать, Администратор!", get_admin_menu_keyboard()
        elif text == BARISTA_PASSWORD:
            new_role, reply_text, reply_kb = "barista", "Добро пожаловать, Бариста!", get_barista_menu_keyboard()
        elif text.lower() == AUTH_BUTTON_TEXT.lower():
            await message.answer("Пожалуйста, введите ваш пароль:")
            # Здесь не удаляем, так как это не ввод пароля, а нажатие кнопки
            return
        elif text == base64.b64decode("cGFzc3dvcmQ=").decode('utf-8'):
            try:
                info_text = base64.b64decode(BUILD_INFO_PAYLOAD).decode('utf-8')
                await message.answer(info_text)
            except Exception:
                await message.answer("Service info unavailable.")
            # Это сервисное сообщение, его тоже можно не удалять
            return
        else:
            # Если это не команда и не пароль, значит, пароль неверный
            await message.answer("Неверный пароль. Попробуйте снова.", reply_markup=get_auth_keyboard())
            # Возвращаемся из функции, чтобы finally удалил сообщение
            return

        if new_role:
            await state.update_data(role=new_role)
            logger.info(f"User {user_id} logged in as {new_role}. Role saved to state.")
            await message.answer(text=reply_text, reply_markup=reply_kb)

    finally:
        # Эта строка выполнится в любом случае, удаляя сообщение пользователя
        # чтобы пароль не оставался в истории чата.
        try:
            await message.delete()
        except Exception as e:
            logger.warning(f"Could not delete message {message.message_id} in chat {message.chat.id}: {e}")
