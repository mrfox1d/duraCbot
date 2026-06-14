"""
handlers/admin.py — команды администратора и обработка заявок на прак
"""

import html
import logging
from datetime import date

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID, DEFAULT_TIME_SLOTS
from database import Database
from keyboards import main_menu_kb

logger = logging.getLogger(__name__)
admin_router = Router()


def _escape(text: str) -> str:
    return html.escape(str(text))


def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ─── Фильтр: только для админа ───────────────────────────────────────────────

def _admin_only(message: Message) -> bool:
    return _is_admin(message.from_user.id)


# ─── /add_player ─────────────────────────────────────────────────────────────

@admin_router.message(Command("add_player"))
async def cmd_add_player(message: Message, db: Database) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для этой команды.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "⚠️ Использование: <code>/add_player [ник] [роль]</code>\n"
            "Пример: <code>/add_player xX_Sniper_Xx Снайпер</code>"
        )
        return

    nickname = args[1].strip()
    role = args[2].strip()

    success = await db.add_player(nickname, role)
    if success:
        await message.answer(
            f"✅ Игрок <b>{_escape(nickname)}</b> ({_escape(role)}) добавлен в состав."
        )
    else:
        await message.answer(
            f"❌ Игрок с ником <b>{_escape(nickname)}</b> уже существует."
        )


# ─── /remove_player ──────────────────────────────────────────────────────────

@admin_router.message(Command("remove_player"))
async def cmd_remove_player(message: Message, db: Database) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для этой команды.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "⚠️ Использование: <code>/remove_player [ник]</code>\n"
            "Пример: <code>/remove_player xX_Sniper_Xx</code>"
        )
        return

    nickname = args[1].strip()
    success = await db.remove_player(nickname)
    if success:
        await message.answer(
            f"✅ Игрок <b>{_escape(nickname)}</b> удалён из состава."
        )
    else:
        await message.answer(
            f"❌ Игрок <b>{_escape(nickname)}</b> не найден в составе."
        )


# ─── /set_schedule ───────────────────────────────────────────────────────────

@admin_router.message(Command("set_schedule"))
async def cmd_set_schedule(message: Message, db: Database) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для этой команды.")
        return

    args = message.text.split(maxsplit=1)
    today = date.today().isoformat()

    if len(args) < 2 or not args[1].strip():
        # Ставим дефолтное расписание
        time_slots = DEFAULT_TIME_SLOTS
        note = "Стандартное расписание"
    else:
        time_slots = args[1].strip()
        note = ""

    await db.set_schedule(today, time_slots, note)

    today_fmt = date.today().strftime("%d.%m.%Y")
    await message.answer(
        f"✅ Расписание на <b>{today_fmt}</b> обновлено:\n"
        f"🕐 <code>{_escape(time_slots)}</code>"
    )


# ─── Обработка заявок на прак (Accept / Decline) ─────────────────────────────

@admin_router.callback_query(F.data.startswith("prack_accept:"))
async def cb_prack_accept(call: CallbackQuery, db: Database, bot: Bot) -> None:
    if not _is_admin(call.from_user.id):
        await call.answer("⛔ Нет прав.", show_alert=True)
        return

    request_id = int(call.data.split(":")[1])
    request = await db.get_prack_request(request_id)

    if not request:
        await call.answer("❌ Заявка не найдена.", show_alert=True)
        return

    if request["status"] != "pending":
        await call.answer("ℹ️ Заявка уже обработана.", show_alert=True)
        return

    await db.update_prack_status(request_id, "accepted")

    await call.message.edit_text(
        call.message.html_text + "\n\n✅ <b>Заявка принята</b>",
        reply_markup=None,
    )
    await call.answer("✅ Заявка принята")

    logger.info(
        "Заявка #%d от '%s' принята администратором",
        request_id,
        request["team_name"],
    )


@admin_router.callback_query(F.data.startswith("prack_decline:"))
async def cb_prack_decline(call: CallbackQuery, db: Database, bot: Bot) -> None:
    if not _is_admin(call.from_user.id):
        await call.answer("⛔ Нет прав.", show_alert=True)
        return

    request_id = int(call.data.split(":")[1])
    request = await db.get_prack_request(request_id)

    if not request:
        await call.answer("❌ Заявка не найдена.", show_alert=True)
        return

    if request["status"] != "pending":
        await call.answer("ℹ️ Заявка уже обработана.", show_alert=True)
        return

    await db.update_prack_status(request_id, "declined")

    await call.message.edit_text(
        call.message.html_text + "\n\n❌ <b>Заявка отклонена</b>",
        reply_markup=None,
    )
    await call.answer("❌ Заявка отклонена")

    logger.info(
        "Заявка #%d от '%s' отклонена администратором",
        request_id,
        request["team_name"],
    )