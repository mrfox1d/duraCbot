"""
config.py — конфигурация и константы бота
"""

import os

# ─── Токен бота (замени или задай через переменную окружения) ─────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ─── ID администратора клана (Telegram user_id) ───────────────────────────────
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "123456789"))

# ─── ID командного чата (отрицательное число для групп/супергрупп) ────────────
TEAM_CHAT_ID: int = int(os.getenv("TEAM_CHAT_ID", "-1001234567890"))

# ─── Ссылка на канал со скринами праков ──────────────────────────────────────
SCREENSHOTS_CHANNEL_URL: str = "https://t.me/durac_team_screens"

# ─── Ссылка на Parallel (заглушка) ───────────────────────────────────────────
PARALLEL_LINK: str = "https://parallel.com/durac"

# ─── Тег и название команды ───────────────────────────────────────────────────
TEAM_TAG: str = "[duraC]"
TEAM_NAME: str = "duraC Team eSports"

# ─── Таймзона для планировщика ────────────────────────────────────────────────
TIMEZONE: str = "Europe/Moscow"

# ─── Расписание по умолчанию (если не задано командой) ───────────────────────
DEFAULT_TIME_SLOTS: str = "19:00, 20:00, 21:00"
