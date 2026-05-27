from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from services.launchpad_monitor import scan_launchpads
from services.twitter_scraper import scan_twitter
from loguru import logger

scheduler = AsyncIOScheduler()

async def start_scheduler(bot: Bot):
    # Launchpad monitor every 2 minutes
    scheduler.add_job(scan_launchpads, 'interval', minutes=2, args=[bot])
    # Twitter/X monitor every 4 minutes
    scheduler.add_job(scan_twitter, 'interval', minutes=4, args=[bot])
    scheduler.start()
    logger.info("🚀 Scheduler started - Launchpads (2min) + X/Twitter (4min)")