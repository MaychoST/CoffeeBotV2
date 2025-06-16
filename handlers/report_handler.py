# Имя файла: handlers/report_handler.py (ФИНАЛЬНАЯ ВЕРСИЯ)

import logging
from datetime import date, timedelta
import asyncpg

from aiogram import Router, F, html
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.exceptions import TelegramBadRequest
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

from states import ReportStates
from keyboards import get_reports_menu_keyboard, get_admin_menu_keyboard
from database import get_sales_summary_for_period, get_sold_items_details_for_period
from constants import (CURRENCY_SYMBOL, REPORTS_MENU_TEXT, SALES_TODAY_TEXT,
                       SALES_YESTERDAY_TEXT, SALES_PERIOD_TEXT, BACK_TO_ADMIN_MAIN_MENU_TEXT)

router = Router()
logger = logging.getLogger(__name__)


async def check_admin_auth(target: Message | CallbackQuery, state: FSMContext) -> bool:
    data = await state.get_data()
    if data.get('role') == 'admin': return True
    if isinstance(target, CallbackQuery):
        await target.answer("Эта функция доступна только администратору.", show_alert=True)
    else:
        await target.answer("Эта функция доступна только администратору.")
    return False


async def generate_and_send_report(message: Message, db_pool: asyncpg.Pool, start_date: date, end_date: date):
    temp_msg = await message.answer("⏳ Минутку, собираю данные...")

    # <<< ИЗМЕНЕНИЕ: Передаем db_pool
    order_count, total_sales = await get_sales_summary_for_period(db_pool, start_date, end_date)
    sold_items_details = await get_sold_items_details_for_period(db_pool, start_date, end_date)

    date_range_str = f"за <b>{start_date.strftime('%d.%m.%Y')}</b>" if start_date == end_date else f"с <b>{start_date.strftime('%d.%m.%Y')}</b> по <b>{end_date.strftime('%d.%m.%Y')}</b>"
    response_text = f"📊 <b>Отчет по заказам {date_range_str}:</b>\n\n"

    if order_count > 0:
        response_text += f"Количество завершенных заказов: <b>{order_count}</b>\n"
        response_text += f"Общая сумма продаж: <b>{total_sales:.2f} {CURRENCY_SYMBOL}</b>\n"
        avg_check = total_sales / order_count
        response_text += f"Средний чек: <b>{avg_check:.2f} {CURRENCY_SYMBOL}</b>\n"
        if sold_items_details:
            response_text += "\n<b>Детализация по проданным товарам:</b>\n"
            for item in sold_items_details:
                response_text += f"  - {html.quote(str(item['item_name']))}: {item['total_quantity_sold']} шт.\n"
    else:
        response_text += "Завершенных заказов в этот период не найдено."

    await temp_msg.delete()
    await message.answer(response_text, reply_markup=get_reports_menu_keyboard())


@router.message(F.text == REPORTS_MENU_TEXT, StateFilter(None))
async def reports_menu_entry(message: Message, state: FSMContext):
    if not await check_admin_auth(message, state): return
    await message.answer("Выберите нужный отчет:", reply_markup=get_reports_menu_keyboard())


@router.message(F.text.in_({SALES_TODAY_TEXT, SALES_YESTERDAY_TEXT}), StateFilter(None))
async def report_sales_today_or_yesterday(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(message, state): return
    target_date = date.today() if message.text == SALES_TODAY_TEXT else date.today() - timedelta(days=1)
    await generate_and_send_report(message, db_pool, target_date, target_date)


@router.message(F.text == SALES_PERIOD_TEXT, StateFilter(None))
async def report_sales_period_start(message: Message, state: FSMContext):
    if not await check_admin_auth(message, state): return
    await state.set_state(ReportStates.waiting_for_start_date)
    await message.answer("Выберите <b>начальную</b> дату периода:",
                         reply_markup=await SimpleCalendar().start_calendar())


async def process_date_selection(callback_query: CallbackQuery, selected_date: date, state: FSMContext,
                                 db_pool: asyncpg.Pool):
    current_state_str = await state.get_state();
    message = callback_query.message

    if current_state_str == ReportStates.waiting_for_start_date:
        if selected_date > date.today():
            await callback_query.answer("Начальная дата не может быть в будущем.", show_alert=True)
            await callback_query.message.edit_reply_markup(reply_markup=await SimpleCalendar().start_calendar());
            return

        await state.update_data(report_start_date=selected_date.isoformat())
        await state.set_state(ReportStates.waiting_for_end_date)
        await message.edit_text(
            f"Начальная дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\nТеперь выберите <b>конечную</b> дату:",
            reply_markup=await SimpleCalendar().start_calendar(year=selected_date.year, month=selected_date.month))

    elif current_state_str == ReportStates.waiting_for_end_date:
        data = await state.get_data();
        start_date = date.fromisoformat(data.get("report_start_date"))
        if start_date > selected_date:
            await callback_query.answer("Конечная дата не может быть раньше начальной. Выберите дату заново.",
                                        show_alert=True)
            await state.set_state(ReportStates.waiting_for_end_date)
            await callback_query.message.edit_text(
                f"Начальная дата: <b>{start_date.strftime('%d.%m.%Y')}</b>\nПожалуйста, выберите <b>конечную</b> дату:",
                reply_markup=await SimpleCalendar().start_calendar(year=start_date.year, month=start_date.month));
            return
        auth_data = await state.get_data();
        await state.clear();
        await state.set_data(auth_data)
        await callback_query.message.delete()
        await generate_and_send_report(callback_query.message, db_pool, start_date, selected_date)


@router.callback_query(SimpleCalendarCallback.filter(),
                       StateFilter(ReportStates.waiting_for_start_date, ReportStates.waiting_for_end_date))
async def process_calendar_action(callback_query: CallbackQuery, callback_data: SimpleCalendarCallback,
                                  state: FSMContext, db_pool: asyncpg.Pool):
    if not await check_admin_auth(callback_query, state): return

    if callback_data.act == "CANCEL":
        auth_data = await state.get_data();
        await state.clear();
        await state.set_data(auth_data)
        await callback_query.message.edit_text("Выбор периода отменен.", reply_markup=None)
        await callback_query.message.answer("Меню отчетов:", reply_markup=get_reports_menu_keyboard())
        await callback_query.answer();
        return

    if callback_data.act == "TODAY":
        await process_date_selection(callback_query, date.today(), state, db_pool);
        return

    calendar = SimpleCalendar(show_alerts=True)
    try:
        selected, selected_date_obj = await calendar.process_selection(callback_query, callback_data)
        if selected: await process_date_selection(callback_query, selected_date_obj.date(), state, db_pool)
    except TelegramBadRequest:
        await callback_query.answer("Сообщение не изменено, игнорирую.")
