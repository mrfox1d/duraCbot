"""
database.py — инициализация БД и все запросы (AIOSQLite)
"""

import logging
from datetime import date
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = "durac_bot.db"


class Database:
    """Обёртка над aiosqlite с методами для всех таблиц."""

    def __init__(self, path: str = DB_PATH) -> None:
        self.path = path

    # ─── Инициализация ────────────────────────────────────────────────────────

    async def init(self) -> None:
        """Создаём таблицы, если не существуют."""
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS roster (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    nickname TEXT    NOT NULL UNIQUE,
                    role     TEXT    NOT NULL
                );

                CREATE TABLE IF NOT EXISTS schedule (
                    date       TEXT PRIMARY KEY,
                    time_slots TEXT NOT NULL,
                    notes      TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS prack_requests (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_name      TEXT    NOT NULL,
                    contact        TEXT    NOT NULL,
                    requested_time TEXT    NOT NULL,
                    status         TEXT    NOT NULL DEFAULT 'pending'
                );

                CREATE TABLE IF NOT EXISTS match_responses (
                    match_id INTEGER NOT NULL,
                    user_id  INTEGER NOT NULL,
                    username TEXT    NOT NULL,
                    status   TEXT    NOT NULL,
                    PRIMARY KEY (match_id, user_id)
                );
                """
            )
            await db.commit()
        logger.info("БД инициализирована: %s", self.path)

    # ─── Roster ───────────────────────────────────────────────────────────────

    async def add_player(self, nickname: str, role: str) -> bool:
        """Добавить игрока. Возвращает False если ник уже занят."""
        try:
            async with aiosqlite.connect(self.path) as db:
                await db.execute(
                    "INSERT INTO roster (nickname, role) VALUES (?, ?)",
                    (nickname, role),
                )
                await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def remove_player(self, nickname: str) -> bool:
        """Удалить игрока. Возвращает False если игрок не найден."""
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "DELETE FROM roster WHERE nickname = ?", (nickname,)
            )
            await db.commit()
        return cursor.rowcount > 0

    async def get_roster(self) -> list[dict]:
        """Получить весь актуальный состав."""
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT nickname, role FROM roster ORDER BY id")
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ─── Schedule ─────────────────────────────────────────────────────────────

    async def set_schedule(
        self, day: str, time_slots: str, notes: str = ""
    ) -> None:
        """Установить / обновить расписание на дату (формат YYYY-MM-DD)."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO schedule (date, time_slots, notes)
                VALUES (?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    time_slots = excluded.time_slots,
                    notes      = excluded.notes
                """,
                (day, time_slots, notes),
            )
            await db.commit()

    async def get_schedule(self, day: str) -> Optional[dict]:
        """Получить расписание на конкретную дату или None."""
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT date, time_slots, notes FROM schedule WHERE date = ?", (day,)
            )
            row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_today_schedule(self) -> Optional[dict]:
        today = date.today().isoformat()
        return await self.get_schedule(today)

    # ─── Prack requests ───────────────────────────────────────────────────────

    async def add_prack_request(
        self, team_name: str, contact: str, requested_time: str
    ) -> int:
        """Сохранить заявку. Возвращает ID новой записи."""
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO prack_requests (team_name, contact, requested_time, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (team_name, contact, requested_time),
            )
            await db.commit()
            return cursor.lastrowid

    async def update_prack_status(self, request_id: int, status: str) -> None:
        """Обновить статус заявки: 'accepted' или 'declined'."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE prack_requests SET status = ? WHERE id = ?",
                (status, request_id),
            )
            await db.commit()

    async def get_prack_request(self, request_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM prack_requests WHERE id = ?", (request_id,)
            )
            row = await cursor.fetchone()
        return dict(row) if row else None

    # ─── Match responses ──────────────────────────────────────────────────────

    async def upsert_match_response(
        self, match_id: int, user_id: int, username: str, status: str
    ) -> None:
        """Создать или обновить отклик игрока на матч."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO match_responses (match_id, user_id, username, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(match_id, user_id) DO UPDATE SET
                    status   = excluded.status,
                    username = excluded.username
                """,
                (match_id, user_id, username, status),
            )
            await db.commit()

    async def get_match_responses(self, match_id: int) -> list[dict]:
        """Получить все отклики по ID матч-сообщения."""
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_id, username, status FROM match_responses WHERE match_id = ?",
                (match_id,),
            )
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def clear_match_responses(self, match_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "DELETE FROM match_responses WHERE match_id = ?", (match_id,)
            )
            await db.commit()