"""
handlers/user.py — пользовательские хэндлеры и FSM для оформления прака
"""

import html
import logging
from datetime import date

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID, SCREENSHOTS_CHANNEL_URL, TEAM_TAG, TEAM_NAME
from database import Database
from keyboards import (
    back_to_menu_kb,
    main_menu_kb,
    match_availability_kb,
    prack_request_admin_kb,
)

logger = logging.getLogger(__name__)
user_router = Router()


# ─── FSM для заявки на прак ──────────────────────────────────────────────────

class PrackForm(StatesGroup):
    team_name = State()
    contact = State()
    requested_time = State()


# ─── Вспомогательная функция форматирования ──────────────────────────────────

def _escape(text: str) -> str:
    """Экранирует строку для HTML-разметки Telegram."""
    return html.escape(str(text))


def _format_roster(players: list[dict]) -> str:
    if not players:
        return "👥 Состав пока пуст."
    lines = [f"<b>👥 {_escape(TEAM_NAME)} | Состав</b>\n"]
    for p in players:
        nick = _escape(p["nickname"])
        role = _escape(p["role"])
        lines.append(f"  🔹 <b>{_escape(TEAM_TAG)}{nick}</b> — <i>{role}</i>")
    return "\n".join(lines)


def _format_schedule(schedule: dict | None) -> str:
    today_str = date.today().strftime("%d.%m.%Y")
    if not schedule:
        return (
            f"📅 <b>Расписание на {today_str}</b>\n\n"
            "На сегодня праков пока не запланировано."
        )
    slots = _escape(schedule["time_slots"])
    notes = _escape(schedule.get("notes") or "")
    text = f"📅 <b>Расписание на {today_str}</b>\n\n🕐 Слоты: <code>{slots}</code>"
    if notes:
        text += f"\n📌 Заметки: {notes}"
    return text


# ─── /start ───────────────────────────────────────────────────────────────────

@user_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"🎮 <b>{_escape(TEAM_NAME)}</b>\n\n"
        "Добро пожаловать! Выбери раздел:",
        reply_markup=main_menu_kb(),
    )


# ─── Главное меню (callback) ─────────────────────────────────────────────────

@user_router.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        f"🎮 <b>{_escape(TEAM_NAME)}</b>\n\nВыбери раздел:",
        reply_markup=main_menu_kb(),
    )
    await call.answer()


# ─── Скрины с праков ─────────────────────────────────────────────────────────

@user_router.callback_query(F.data == "screenshots")
async def cb_screenshots(call: CallbackQuery) -> None:
    await call.message.edit_text(
        f"🖼 <b>Скрины с праков</b>\n\n"
        f"Все скриншоты с тренировок и праков публикуются в нашем канале:\n"
        f"🔗 <a href=\"{SCREENSHOTS_CHANNEL_URL}\">{_escape(TEAM_NAME)} | Screens</a>\n\n"
        "<i>Заходи, смотри, вдохновляйся 🔥</i>",
        reply_markup=back_to_menu_kb(),
    )
    await call.answer()


# ─── Актуальный состав ────────────────────────────────────────────────────────

@user_router.callback_query(F.data == "roster")
async def cb_roster(call: CallbackQuery, db: Database) -> None:
    players = await db.get_roster()
    await call.message.edit_text(
        _format_roster(players),
        reply_markup=back_to_menu_kb(),
    )
    await call.answer()


# ─── Расписание на сегодня ────────────────────────────────────────────────────

@user_router.callback_query(F.data == "schedule_today")
async def cb_schedule_today(call: CallbackQuery, db: Database) -> None:
    schedule = await db.get_today_schedule()
    await call.message.edit_text(
        _format_schedule(schedule),
        reply_markup=back_to_menu_kb(),
    )
    await call.answer()


# ─── FSM: Оформить прак ──────────────────────────────────────────────────────

@user_router.callback_query(F.data == "request_prack")
async def cb_request_prack_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PrackForm.team_name)
    await call.message.edit_text(
        "🎮 <b>Оформление заявки на прак</b>\n\n"
        "<b>Шаг 1 / 3</b>\n"
        "Введите <b>название вашего клана</b>:",
        reply_markup=back_to_menu_kb(),
    )
    await call.answer()


@user_router.message(PrackForm.team_name)
async def fsm_team_name(message: Message, state: FSMContext) -> None:
    await state.update_data(team_name=message.text.strip())
    await state.set_state(PrackForm.contact)
    await message.answer(
        "🎮 <b>Оформление заявки на прак</b>\n\n"
        "<b>Шаг 2 / 3</b>\n"
        "Укажите <b>ссылку для связи</b> (Telegram, Discord и т.д.):"
    )


@user_router.message(PrackForm.contact)
async def fsm_contact(message: Message, state: FSMContext) -> None:
    await state.update_data(contact=message.text.strip())
    await state.set_state(PrackForm.requested_time)
    await message.answer(
        "🎮 <b>Оформление заявки на прак</b>\n\n"
        "<b>Шаг 3 / 3</b>\n"
        "Укажите <b>желаемое время</b> прака (например: <code>19:00</code>):"
    )


@user_router.message(PrackForm.requested_time)
async def fsm_requested_time(
    message: Message, state: FSMContext, db: Database, bot: Bot
) -> None:
    data = await state.get_data()
    await state.clear()

    team_name = data["team_name"]
    contact = data["contact"]
    requested_time = message.text.strip()

    request_id = await db.add_prack_request(team_name, contact, requested_time)

    await message.answer(
        "✅ <b>Заявка отправлена!</b>\n\n"
        "Мы рассмотрим её в ближайшее время. Ожидайте ответа.",
        reply_markup=main_menu_kb(),
    )

    # Уведомление администратору
    admin_text = (
        f"📬 <b>Новая заявка на прак #{request_id}</b>\n\n"
        f"👥 Клан: <b>{_escape(team_name)}</b>\n"
        f"🔗 Связь: {_escape(contact)}\n"
        f"🕐 Желаемое время: <b>{_escape(requested_time)}</b>\n\n"
        "Выберите действие:"
    )
    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=prack_request_admin_kb(request_id),
        )
    except Exception as exc:
        logger.error("Не удалось уведомить админа: %s", exc)


# ─── Отклики на матч (командный чат) ─────────────────────────────────────────

async def _update_match_message(
    call: CallbackQuery,
    match_id: int,
    db: Database,
    status: str,
) -> None:
    """Сохраняет отклик и перерисовывает сообщение с актуальным стаком."""
    username = call.from_user.username or call.from_user.full_name
    await db.upsert_match_response(
        match_id=match_id,
        user_id=call.from_user.id,
        username=username,
        status=status,
    )

    responses = await db.get_match_responses(match_id)
    can_play = [r for r in responses if r["status"] == "can_play"]
    cannot_play = [r for r in responses if r["status"] == "cannot_play"]

    def _fmt_list(players: list[dict]) -> str:
        return (
            "\n".join(f"  • @{_escape(p['username'])}" for p in players)
            if players
            else "  <i>— пока никого —</i>"
        )

    # Восстанавливаем текст расписания из текущего сообщения (первая часть)
    original_lines = (call.message.text or "").split("\n\n🟢")[0]
    new_text = (
        f"{original_lines}\n\n"
        f"🟢 <b>Смогут ({len(can_play)}):</b>\n{_fmt_list(can_play)}\n\n"
        f"🔴 <b>Не смогут ({len(cannot_play)}):</b>\n{_fmt_list(cannot_play)}"
    )

    try:
        await call.message.edit_text(
            new_text,
            reply_markup=match_availability_kb(match_id),
        )
    except Exception:
        pass  # Сообщение не изменилось — игнорируем


@user_router.callback_query(F.data.startswith("match_can:"))
async def cb_match_can(call: CallbackQuery, db: Database) -> None:
    match_id = int(call.data.split(":")[1])
    await _update_match_message(call, match_id, db, "can_play")
    await call.answer("✅ Записался!")


@user_router.callback_query(F.data.startswith("match_cannot:"))
async def cb_match_cannot(call: CallbackQuery, db: Database) -> None:
    match_id = int(call.data.split(":")[1])
    await _update_match_message(call, match_id, db, "cannot_play")
    await call.answer("❌ Принято, жаль")
