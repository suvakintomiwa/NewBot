from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from services.launchpad_monitor import scan_launchpads
from config.settings import settings
from loguru import logger

scheduler = AsyncIOScheduler()

async def start_scheduler(bot: Bot):
    # Scan launchpads every 1 minute
    scheduler.add_job(scan_launchpads, 'interval', minutes=1, args=[bot])
    scheduler.start()
    logger.info("🚀 Scheduler started - Launchpad monitor every 1 minute")