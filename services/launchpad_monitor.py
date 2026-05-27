import aiohttp
from datetime import datetime, timedelta, timezone
from loguru import logger
from config.settings import settings
from aiogram import Bot
from database.db import get_connection
from typing import List, Dict
import asyncio

DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"
DEXSCREENER_SEARCH = "https://api.dexscreener.com/latest/dex/search"

def is_new_project(address: str) -> bool:
    """Check if we've already alerted about this project"""
    if not address:
        return False
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM seen_projects WHERE address = ?",
        (address,)
    ).fetchone()
    conn.close()
    return row is None

def mark_as_seen(address: str):
    """Remember that we alerted about this project"""
    if not address:
        return
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO seen_projects (address, chain) VALUES (?, ?)",
            (address, "multi")
        )
        conn.commit()
    except Exception as e:
        logger.error(f"DB error: {e}")
    finally:
        conn.close()

async def search_new_tokens(query: str) -> List[Dict]:
    """Search DexScreener for new tokens"""
    url = f"{DEXSCREENER_SEARCH}?q={query}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                pairs = data.get("pairs", [])[:15]
                
                now = datetime.now(timezone.utc)
                results = []
                for pair in pairs:
                    created_at = pair.get("pairCreatedAt")
                    if not created_at:
                        continue
                    
                    created = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
                    age_minutes = (now - created).total_seconds() / 60
                    
                    # Show anything under 30 minutes old
                    if age_minutes > 30:
                        continue
                    
                    token = pair.get("baseToken", {})
                    address = token.get("address", "")
                    
                    if not is_new_project(address):
                        continue
                    
                    chain = pair.get("chainId", "unknown")
                    price = pair.get("priceUsd", "0")
                    liquidity = pair.get("liquidity", {}).get("usd", 0)
                    volume = pair.get("volume", {}).get("h24", 0)
                    fdv = pair.get("fdv", 0)
                    
                    # Extract socials
                    twitter = None
                    telegram = None
                    socials = pair.get("info", {}).get("socials", [])
                    for s in socials:
                        s_type = s.get("type", "")
                        if "twitter" in s_type:
                            twitter = s.get("url")
                        elif "telegram" in s_type:
                            telegram = s.get("url")
                    
                    results.append({
                        "name": token.get("name", "Unknown"),
                        "symbol": token.get("symbol", "Unknown"),
                        "address": address,
                        "chain": chain,
                        "price": price,
                        "liquidity": liquidity,
                        "volume": volume,
                        "fdv": fdv,
                        "twitter": twitter,
                        "telegram": telegram,
                        "url": f"https://dexscreener.com/{chain}/{pair.get('pairAddress', '')}",
                        "age_minutes": round(age_minutes, 1)
                    })
                return results
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

async def get_new_pump_fun() -> List[Dict]:
    """Fetch newest tokens from Pump.fun"""
    url = "https://frontend-api.pump.fun/coins?offset=0&limit=50&sort=created&order=DESC&includeNsfw=false"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                tokens = data if isinstance(data, list) else data.get("coins", [])
                
                now = datetime.now(timezone.utc)
                results = []
                for t in tokens[:30]:
                    address = t.get("mint", t.get("address", ""))
                    
                    if not is_new_project(address):
                        continue
                    
                    created_at = t.get("created_at", 0)
                    if isinstance(created_at, str):
                        try:
                            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        except:
                            created = now - timedelta(hours=1)
                    else:
                        created = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
                    
                    age_minutes = (now - created).total_seconds() / 60
                    
                    if age_minutes > 30:
                        continue
                    
                    twitter = t.get("twitter", t.get("twitter_link"))
                    telegram = t.get("telegram", t.get("telegram_link"))
                    
                    results.append({
                        "name": t.get("name", "Unknown"),
                        "symbol": t.get("symbol", "Unknown"),
                        "address": address,
                        "chain": "solana",
                        "price": t.get("usd_market_cap", 0),
                        "liquidity": 0,
                        "volume": t.get("usd_volume_24h", 0),
                        "fdv": t.get("usd_market_cap", 0),
                        "twitter": twitter,
                        "telegram": telegram,
                        "url": f"https://pump.fun/coin/{address}",
                        "age_minutes": round(age_minutes, 1)
                    })
                return results
    except Exception as e:
        logger.error(f"Pump.fun error: {e}")
        return []

async def scan_launchpads(bot: Bot):
    """Main scanner - check all sources"""
    logger.info("🔍 Scanning for new projects...")
    
    all_projects = []
    
    # Search for latest tokens using common queries
    search_terms = ["/", "v2", "v3", "sol", "eth", "pepe", "dog", "cat", "ai", "meme"]
    for term in search_terms:
        results = await search_new_tokens(term)
        all_projects.extend(results)
        await asyncio.sleep(0.3)
    
    # Pump.fun
    pf_tokens = await get_new_pump_fun()
    all_projects.extend(pf_tokens)
    
    # Deduplicate by address
    seen_addresses = set()
    unique_projects = []
    for proj in all_projects:
        addr = proj.get("address", "")
        if addr and addr not in seen_addresses:
            seen_addresses.add(addr)
            unique_projects.append(proj)
    
    if not unique_projects:
        logger.info("No new projects found.")
        return
    
    # Sort by age (newest first)
    unique_projects.sort(key=lambda x: x.get("age_minutes", 99))
    
    alerted = 0
    for proj in unique_projects[:5]:  # Max 5 per scan to avoid spam
        # Build message
        text = f"🆕 <b>NEW PROJECT</b>\n\n"
        text += f"📛 <b>{proj['name']}</b> (${proj.get('symbol', 'N/A')})\n"
        text += f"⛓️ Chain: <b>{proj.get('chain', 'unknown').upper()}</b>\n"
        text += f"⏱️ Age: <b>{proj.get('age_minutes', '?')} min</b>\n"
        
        if proj.get("price") and float(proj["price"]) > 0:
            text += f"💵 Price: ${float(proj['price']):.8f}\n"
        if proj.get("liquidity") and float(proj["liquidity"]) > 0:
            text += f"💧 Liq: ${float(proj['liquidity']):,.0f}\n"
        if proj.get("volume") and float(proj["volume"]) > 0:
            text += f"📈 Vol: ${float(proj['volume']):,.0f}\n"
        
        links = ""
        if proj.get("twitter"):
            links += f"🐦 <a href='{proj['twitter']}'>Twitter</a>  "
        if proj.get("telegram"):
            links += f"📢 <a href='{proj['telegram']}'>TG</a>  "
        links += f"📊 <a href='{proj['url']}'>Chart</a>"
        
        if links.strip():
            text += f"\n{links}"
        
        try:
            await bot.send_message(settings.ADMIN_ID, text, disable_web_page_preview=True)
            mark_as_seen(proj["address"])
            alerted += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Send error: {e}")
    
    logger.info(f"✅ Sent {alerted} alerts")