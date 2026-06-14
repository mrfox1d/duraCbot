"""
scheduler.py — задачи APScheduler: дневной анонс и пинг за 15 минут до прака
"""

import html
import logging
from datetime import date, datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import PARALLEL_LINK, TEAM_CHAT_ID, TEAM_NAME, TIMEZONE
from database import Database
from keyboards import match_availability_kb

logger = logging.getLogger(__name__)


def _escape(text: str) -> str:
    return html.escape(str(text))


def _parse_first_slot(time_slots: str) -> datetime | None:
    """Берёт первый временной слот из строки и возвращает datetime на сегодня."""
    try:
        first = time_slots.split(",")[0].strip()  # "19:00"
        hour, minute = map(int, first.split(":"))
        today = date.today()
        return datetime(today.year, today.month, today.day, hour, minute)
    except (ValueError, IndexError):
        return None


async def _send_daily_schedule(bot: Bot, db: Database) -> None:
    """Ежедневная задача в 12:00 МСК: публикует расписание + кнопки в командном чате."""
    schedule = await db.get_today_schedule()
    today_fmt = date.today().strftime("%d.%m.%Y")

    if not schedule:
        text = (
            f"📅 <b>Расписание на {today_fmt}</b>\n\n"
            "На сегодня праков пока не запланировано.\n\n"
            f"<i>— {_escape(TEAM_NAME)}</i>"
        )
        try:
            await bot.send_message(TEAM_CHAT_ID, text)
        except Exception as exc:
            logger.error("Ошибка отправки расписания: %s", exc)
        return

    slots = _escape(schedule["time_slots"])
    notes = _escape(schedule.get("notes") or "")
    text = (
        f"📅 <b>Расписание на {today_fmt}</b>\n\n"
        f"🕐 Слоты: <code>{slots}</code>"
    )
    if notes:
        text += f"\n📌 {notes}"
    text += (
        "\n\n<b>Стак на прак 💪</b>\n"
        "Отметься, сможешь ли сегодня:\n\n"
        "🟢 <b>Смогут (0):</b>\n  <i>— пока никого —</i>\n\n"
        "🔴 <b>Не смогут (0):</b>\n  <i>— пока никого —</i>"
    )

    try:
        sent = await bot.send_message(
            TEAM_CHAT_ID,
            text,
            reply_markup=match_availability_kb(0),  # временный ID
        )

        # Используем message_id как match_id и перерисовываем клавиатуру
        match_id = sent.message_id
        await sent.edit_reply_markup(reply_markup=match_availability_kb(match_id))

        # Закрепляем сообщение
        await bot.pin_chat_message(
            chat_id=TEAM_CHAT_ID,
            message_id=match_id,
            disable_notification=True,
        )

        # Планируем пинг за 15 минут до первого слота
        first_slot_dt = _parse_first_slot(schedule["time_slots"])
        if first_slot_dt:
            remind_at = first_slot_dt - timedelta(minutes=15)
            now = datetime.now()
            if remind_at > now:
                from apscheduler.schedulers.asyncio import AsyncIOScheduler
                # Получаем существующий планировщик через bot (прокинут через замыкание)
                scheduler: AsyncIOScheduler = bot._scheduler  # type: ignore[attr-defined]
                scheduler.add_job(
                    _send_prack_reminder,
                    trigger="date",
                    run_date=remind_at,
                    args=[bot, db, match_id],
                    id=f"remind_{date.today().isoformat()}",
                    replace_existing=True,
                )
                logger.info("Пинг запланирован на %s", remind_at.strftime("%H:%M"))

        logger.info("Расписание опубликовано, match_id=%d", match_id)

    except Exception as exc:
        logger.error("Ошибка публикации расписания: %s", exc)


async def _send_prack_reminder(bot: Bot, db: Database, match_id: int) -> None:
    """Отправляет пинг участников за 15 минут до прака."""
    responses = await db.get_match_responses(match_id)
    can_play = [r for r in responses if r["status"] == "can_play"]

    if not can_play:
        logger.info("Нет участников для пинга, пропускаем.")
        return

    mentions = " ".join(f"@{_escape(p['username'])}" for p in can_play)
    text = (
        f"⚠️ <b>До прака осталось 15 минут!</b>\n\n"
        f"{mentions}\n\n"
        f"Залетаем в Parallel: {PARALLEL_LINK}"
    )

    try:
        await bot.send_message(TEAM_CHAT_ID, text)
        logger.info("Пинг отправлен: %d участников", len(can_play))
    except Exception as exc:
        logger.error("Ошибка отправки пинга: %s", exc)


def setup_scheduler(bot: Bot, db: Database) -> AsyncIOScheduler:
    """Инициализирует и возвращает планировщик."""
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    # Прокидываем планировщик в объект bot для доступа изнутри задач
    bot._scheduler = scheduler  # type: ignore[attr-defined]

    # Ежедневно в 12:00 МСК
    scheduler.add_job(
        _send_daily_schedule,
        trigger=CronTrigger(hour=12, minute=0, timezone=TIMEZONE),
        args=[bot, db],
        id="daily_schedule",
        replace_existing=True,
    )

    logger.info("Задача daily_schedule зарегистрирована (12:00 МСК)")
    return scheduler
