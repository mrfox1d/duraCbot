"""
keyboards.py — все Inline-клавиатуры бота
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню пользователя."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🖼 Скрины с праков", callback_data="screenshots")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Актуальный состав", callback_data="roster")
    )
    builder.row(
        InlineKeyboardButton(text="📅 Расписание на сегодня", callback_data="schedule_today")
    )
    builder.row(
        InlineKeyboardButton(text="🎮 Оформить прак", callback_data="request_prack")
    )
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")
    )
    return builder.as_markup()


def prack_request_admin_kb(request_id: int) -> InlineKeyboardMarkup:
    """Кнопки для администратора: принять/отклонить заявку на прак."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Принять",
            callback_data=f"prack_accept:{request_id}",
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"prack_decline:{request_id}",
        ),
    )
    return builder.as_markup()


def match_availability_kb(match_id: int) -> InlineKeyboardMarkup:
    """Кнопки присутствия на матче в командном чате."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Смогу играть",
            callback_data=f"match_can:{match_id}",
        ),
        InlineKeyboardButton(
            text="❌ Не смогу",
            callback_data=f"match_cannot:{match_id}",
        ),
    )
    return builder.as_markup()