import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from config.settings import settings
from database.db import init_db
from handlers import start, ai, commands, crypto, jobs, watchlist, notes
from services.scheduler import start_scheduler
from loguru import logger

async def main():
    logger.add("bot.log", rotation="10 MB", level="INFO")
    logger.info("Starting Web3 Jarvis Bot...")
    init_db()
    logger.info("Database initialized")
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(ai.router)
    dp.include_router(commands.router)
    dp.include_router(crypto.router)
    dp.include_router(jobs.router)
    dp.include_router(watchlist.router)
    dp.include_router(notes.router)
    await start_scheduler(bot)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
