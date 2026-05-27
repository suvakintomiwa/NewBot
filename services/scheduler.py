from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from services.crypto_tracker import get_trending
from services.launchpad_monitor import scan_launchpads
from config.settings import settings
from loguru import logger

scheduler = AsyncIOScheduler()

async def send_alpha_alert(bot: Bot):
    try:
        data = await get_trending()
        if data:
            text = "🔥 ALPHA ALERT\n"
            for coin in data[:3]:
                text += f"• {coin['symbol']} ({coin['change_24h']}%)\n"
            await bot.send_message(settings.ADMIN_ID, text)
    except Exception as e:
        logger.error(f"Alert error: {e}")

async def start_scheduler(bot: Bot):
    scheduler.add_job(send_alpha_alert, 'interval', minutes=1, args=[bot])
    scheduler.add_job(scan_launchpads, 'interval', minutes=1, args=[bot])
    scheduler.start()
    logger.info("Scheduler started (alpha + launchpad monitor every 1 min)")