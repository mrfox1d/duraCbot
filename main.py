"""
main.py — точка входа бота duraC Team eSports
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import Database
from handlers.user import user_router
from handlers.admin import admin_router
from scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    db = Database()
    await db.init()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Прокидываем БД в хэндлеры через workflow_data
    dp["db"] = db

    dp.include_router(user_router)
    dp.include_router(admin_router)

    scheduler = setup_scheduler(bot, db)
    scheduler.start()
    logger.info("APScheduler запущен")

    try:
        logger.info("Бот duraC Team eSports запускается...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())