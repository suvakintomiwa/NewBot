import aiohttp
from datetime import datetime, timedelta, timezone
from loguru import logger
from config.settings import settings
from aiogram import Bot
from typing import List, Dict

CHAINS = {
    "solana": "solana",
    "ethereum": "ethereum",
    "base": "base",
    "bsc": "bsc"
}

DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"

async def get_new_pairs_dex(chain_id: str) -> List[Dict]:
    """Fetch latest token pairs for a chain and filter by creation time < 2 minutes"""
    url = f"{DEXSCREENER_API}/pairs/{chain_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                pairs = data.get("pairs", [])
                if not pairs:
                    return []
                now = datetime.now(timezone.utc)
                recent = []
                for pair in pairs:
                    created_at = pair.get("pairCreatedAt")
                    if created_at:
                        created = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
                        if (now - created).total_seconds() < 120:  # 2 min window
                            token = pair.get("baseToken", {})
                            # Extract socials if present in info (rare)
                            socials = pair.get("info", {}).get("socials", [])
                            twitter = None
                            telegram = None
                            for s in socials:
                                if s.get("type") == "twitter":
                                    twitter = s.get("url")
                                elif s.get("type") == "telegram":
                                    telegram = s.get("url")
                            # Alternatively, some pairs have "urls" array
                            urls = pair.get("urls", [])
                            for u in urls:
                                if "twitter.com" in u:
                                    twitter = u
                                elif "t.me" in u:
                                    telegram = u
                            recent.append({
                                "name": token.get("name", "Unknown"),
                                "symbol": token.get("symbol", ""),
                                "address": token.get("address", ""),
                                "chain": chain_id,
                                "price": pair.get("priceUsd"),
                                "twitter": twitter,
                                "telegram": telegram,
                                "url": pair.get("url", "")
                            })
                return recent
    except Exception as e:
        logger.error(f"DexScreener error {chain_id}: {e}")
        return []

async def get_new_pump_fun() -> List[Dict]:
    """Fetch newest tokens from Pump.fun (unofficial API)"""
    url = "https://frontend-api.pump.fun/coins?offset=0&limit=10&sort=created&order=DESC&includeNsfw=false"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                tokens = data.get("coins", [])
                now = datetime.now(timezone.utc)
                recent = []
                for t in tokens:
                    created = datetime.fromtimestamp(t["created_at"] / 1000, tz=timezone.utc)
                    if (now - created).total_seconds() < 120:
                        recent.append({
                            "name": t["name"],
                            "symbol": t["symbol"],
                            "address": t["mint"],
                            "chain": "solana",
                            "price": None,
                            "twitter": t.get("twitter"),
                            "telegram": t.get("telegram"),
                            "url": f"https://pump.fun/coin/{t['mint']}"
                        })
                return recent
    except Exception as e:
        logger.error(f"Pump.fun error: {e}")
        return []

async def scan_launchpads(bot: Bot):
    """Scan all sources and send alerts for projects with socials"""
    all_projects = []
    for chain in CHAINS.values():
        pairs = await get_new_pairs_dex(chain)
        all_projects.extend(pairs)
    pf_tokens = await get_new_pump_fun()
    all_projects.extend(pf_tokens)

    if not all_projects:
        logger.info("No new projects found.")
        return

    for proj in all_projects:
        if proj["twitter"] or proj["telegram"]:  # only alert if has social
            text = f"🚀 <b>NEW LAUNCH DETECTED</b>\n"
            text += f"• <b>{proj['name']}</b> ({proj['symbol']}) on {proj['chain'].upper()}\n"
            if proj["twitter"]:
                text += f"• 🐦 <a href='{proj['twitter']}'>Twitter</a>\n"
            if proj["telegram"]:
                text += f"• 📢 <a href='{proj['telegram']}'>Telegram</a>\n"
            if proj["url"]:
                text += f"• 🔗 <a href='{proj['url']}'>Chart</a>"
            try:
                await bot.send_message(settings.ADMIN_ID, text, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")