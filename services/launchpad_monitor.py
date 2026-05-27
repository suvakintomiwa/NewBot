import aiohttp
from datetime import datetime, timedelta, timezone
from loguru import logger
from config.settings import settings
from aiogram import Bot
from database.db import get_connection
from typing import List, Dict, Optional
import asyncio

DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"
COINGECKO_API = "https://api.coingecko.com/api/v3"

# Track multiple launchpads
SOURCES = {
    "pump.fun": "https://frontend-api.pump.fun/coins?offset=0&limit=20&sort=created&order=DESC&includeNsfw=false",
    "moonshot": "https://api.moonshot.cc/coins?limit=20",
}

CHAINS_FOR_DEX = ["solana", "ethereum", "base", "bsc"]

def is_new_project(address: str, chain: str) -> bool:
    """Check if we've already alerted about this project"""
    if not address:
        return False
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM seen_projects WHERE address = ? AND chain = ?",
        (address, chain)
    ).fetchone()
    conn.close()
    return row is None

def mark_as_seen(address: str, chain: str):
    """Remember that we alerted about this project"""
    if not address:
        return
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO seen_projects (address, chain) VALUES (?, ?)",
            (address, chain)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"DB error marking seen: {e}")
    finally:
        conn.close()

async def get_new_pairs_dex(chain_id: str) -> List[Dict]:
    """Fetch newest pairs from DexScreener"""
    url = f"{DEXSCREENER_API}/pairs/{chain_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                pairs = data.get("pairs", [])[:20]  # Top 20 newest
                
                now = datetime.now(timezone.utc)
                recent = []
                for pair in pairs:
                    created_at = pair.get("pairCreatedAt")
                    if not created_at:
                        continue
                    
                    created = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
                    age_minutes = (now - created).total_seconds() / 60
                    
                    # Only alert on projects less than 5 minutes old
                    if age_minutes > 5:
                        continue
                    
                    token = pair.get("baseToken", {})
                    address = token.get("address", "")
                    
                    # Skip if already seen
                    if not is_new_project(address, chain_id):
                        continue
                    
                    # Extract socials
                    twitter = None
                    telegram = None
                    website = None
                    
                    # Check info.socials
                    socials = pair.get("info", {}).get("socials", [])
                    for s in socials:
                        s_type = s.get("type", "").lower()
                        s_url = s.get("url", "")
                        if s_type == "twitter" or "twitter.com" in s_url:
                            twitter = s_url
                        elif s_type == "telegram" or "t.me" in s_url:
                            telegram = s_url
                        elif s_type == "website":
                            website = s_url
                    
                    # Check urls array
                    urls = pair.get("info", {}).get("urls", [])
                    if not urls:
                        urls = pair.get("urls", [])
                    for u in urls:
                        url_str = u.get("url", u) if isinstance(u, dict) else u
                        if "twitter.com" in url_str:
                            twitter = url_str
                        elif "t.me" in url_str or "telegram" in url_str:
                            telegram = url_str
                    
                    price = pair.get("priceUsd", "0")
                    liquidity = pair.get("liquidity", {}).get("usd", 0)
                    volume_24h = pair.get("volume", {}).get("h24", 0)
                    fdv = pair.get("fdv", 0)
                    
                    recent.append({
                        "name": token.get("name", "Unknown"),
                        "symbol": token.get("symbol", "Unknown"),
                        "address": address,
                        "chain": chain_id,
                        "price": price,
                        "liquidity": liquidity,
                        "volume_24h": volume_24h,
                        "fdv": fdv,
                        "twitter": twitter,
                        "telegram": telegram,
                        "website": website,
                        "url": f"https://dexscreener.com/{chain_id}/{pair.get('pairAddress', '')}",
                        "age_minutes": round(age_minutes, 1),
                        "source": "DexScreener"
                    })
                
                return recent
    except Exception as e:
        logger.error(f"DexScreener error for {chain_id}: {e}")
        return []

async def get_new_pump_fun() -> List[Dict]:
    """Fetch newest tokens from Pump.fun"""
    url = SOURCES["pump.fun"]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                tokens = data if isinstance(data, list) else data.get("coins", data.get("data", []))
                
                now = datetime.now(timezone.utc)
                recent = []
                for t in tokens[:20]:
                    address = t.get("mint", t.get("address", t.get("token_address", "")))
                    
                    if not is_new_project(address, "solana"):
                        continue
                    
                    created_at = t.get("created_at", t.get("created_timestamp", 0))
                    if isinstance(created_at, str):
                        try:
                            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        except:
                            created = now - timedelta(hours=1)
                    else:
                        created = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
                    
                    age_minutes = (now - created).total_seconds() / 60
                    
                    if age_minutes > 10:  # Pump.fun tokens move fast, extend window
                        continue
                    
                    twitter = t.get("twitter", t.get("twitter_link", ""))
                    telegram = t.get("telegram", t.get("telegram_link", ""))
                    website = t.get("website", t.get("website_link", ""))
                    
                    recent.append({
                        "name": t.get("name", "Unknown"),
                        "symbol": t.get("symbol", "Unknown"),
                        "address": address,
                        "chain": "solana",
                        "price": t.get("price", t.get("usd_market_cap", 0)),
                        "liquidity": t.get("liquidity", 0),
                        "volume_24h": t.get("volume_24h", t.get("usd_volume_24h", 0)),
                        "fdv": t.get("market_cap", t.get("usd_market_cap", 0)),
                        "twitter": twitter if twitter else None,
                        "telegram": telegram if telegram else None,
                        "website": website if website else None,
                        "url": f"https://pump.fun/coin/{address}" if address else "",
                        "age_minutes": round(age_minutes, 1),
                        "source": "Pump.fun"
                    })
                return recent
    except Exception as e:
        logger.error(f"Pump.fun error: {e}")
        return []

async def get_new_coingecko() -> List[Dict]:
    """Fetch new listings from CoinGecko"""
    url = f"{COINGECKO_API}/coins/list/new"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                recent = []
                for coin in data[:10]:
                    coin_id = coin.get("id", "")
                    if not is_new_project(coin_id, "coingecko"):
                        continue
                    recent.append({
                        "name": coin.get("name", "Unknown"),
                        "symbol": coin.get("symbol", "Unknown"),
                        "address": coin_id,
                        "chain": "multi",
                        "price": None,
                        "liquidity": None,
                        "volume_24h": None,
                        "fdv": None,
                        "twitter": None,
                        "telegram": None,
                        "website": None,
                        "url": f"https://www.coingecko.com/en/coins/{coin_id}",
                        "age_minutes": 0,
                        "source": "CoinGecko New Listings"
                    })
                return recent
    except Exception as e:
        logger.error(f"CoinGecko error: {e}")
        return []

async def scan_launchpads(bot: Bot):
    """Main scanner - check all sources and alert on new projects with socials"""
    logger.info("🔍 Scanning for new projects...")
    
    all_projects = []
    
    # Scan DexScreener for each chain
    for chain in CHAINS_FOR_DEX:
        pairs = await get_new_pairs_dex(chain)
        if pairs:
            logger.info(f"Found {len(pairs)} new pairs on {chain}")
            all_projects.extend(pairs)
        await asyncio.sleep(0.5)  # Rate limit protection
    
    # Scan Pump.fun
    pump_tokens = await get_new_pump_fun()
    if pump_tokens:
        logger.info(f"Found {len(pump_tokens)} new Pump.fun tokens")
        all_projects.extend(pump_tokens)
    
    # Scan CoinGecko new listings
    cg_coins = await get_new_coingecko()
    if cg_coins:
        logger.info(f"Found {len(cg_coins)} new CoinGecko listings")
        all_projects.extend(cg_coins)
    
    if not all_projects:
        logger.info("No new projects found in this scan.")
        return
    
    # Sort by age (newest first)
    all_projects.sort(key=lambda x: x.get("age_minutes", 99))
    
    alerted_count = 0
    for proj in all_projects:
        # Only alert if project has socials (Twitter or Telegram)
        has_social = proj.get("twitter") or proj.get("telegram")
        
        if not has_social:
            # Still mark as seen to avoid rechecking
            mark_as_seen(proj["address"], proj["chain"])
            continue
        
        # Build alert message
        text = f"🚀 <b>NEW LAUNCH DETECTED</b>\n\n"
        text += f"📛 <b>{proj['name']}</b> (${proj['symbol']})\n"
        text += f"⛓️ Chain: <b>{proj['chain'].upper()}</b>\n"
        text += f"⏱️ Age: <b>{proj.get('age_minutes', '?')} min</b>\n"
        text += f"📡 Source: {proj.get('source', 'Unknown')}\n"
        
        if proj.get("price") and float(proj["price"]) > 0:
            text += f"💵 Price: ${float(proj['price']):.8f}\n"
        
        if proj.get("liquidity") and float(proj["liquidity"]) > 0:
            text += f"💧 Liquidity: ${float(proj['liquidity']):,.0f}\n"
        
        if proj.get("fdv") and float(proj["fdv"]) > 0:
            text += f"📊 FDV: ${float(proj['fdv']):,.0f}\n"
        
        if proj.get("volume_24h") and float(proj["volume_24h"]) > 0:
            text += f"📈 24h Vol: ${float(proj['volume_24h']):,.0f}\n"
        
        if proj.get("twitter"):
            text += f"\n🐦 <a href='{proj['twitter']}'>Twitter</a>"
        
        if proj.get("telegram"):
            text += f"  📢 <a href='{proj['telegram']}'>Telegram</a>"
        
        if proj.get("website"):
            text += f"  🌐 <a href='{proj['website']}'>Website</a>"
        
        text += f"\n📊 <a href='{proj['url']}'>View Chart</a>"
        
        try:
            await bot.send_message(
                settings.ADMIN_ID,
                text,
                disable_web_page_preview=True,
                parse_mode="HTML"
            )
            # Mark as seen AFTER successful send
            mark_as_seen(proj["address"], proj["chain"])
            alerted_count += 1
            await asyncio.sleep(0.3)  # Avoid Telegram rate limits
        except Exception as e:
            logger.error(f"Failed to send alert for {proj['name']}: {e}")
    
    logger.info(f"✅ Alerted {alerted_count} new projects out of {len(all_projects)} found")