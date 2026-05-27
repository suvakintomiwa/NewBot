import aiohttp
from datetime import datetime, timedelta, timezone
from loguru import logger
from config.settings import settings
from aiogram import Bot
from database.db import get_connection
from typing import List, Dict
import asyncio

DEXSCREENER_SEARCH = "https://api.dexscreener.com/latest/dex/search"
DEXSCREENER_TOKEN = "https://api.dexscreener.com/latest/dex/tokens"

# All launchpad sources
LAUNCHPADS = {
    "pump.fun": {
        "url": "https://frontend-api.pump.fun/coins?offset=0&limit=50&sort=created&order=DESC&includeNsfw=false",
        "chain": "solana"
    },
    "moonshot": {
        "url": "https://api.moonshot.cc/coins?limit=30&sort=created",
        "chain": "solana"
    },
    "four.meme": {
        "url": "https://four.meme/api/coins?limit=30&sort=created",
        "chain": "bsc"
    },
    "sunpump": {
        "url": "https://sunpump.meme/api/coins?limit=30&sort=created",
        "chain": "tron"
    }
}

# Common search terms to find new pairs on DexScreener
SEARCH_TERMS = ["/", "v2", "v3", "pump", "meme", "pepe", "dog", "cat", "ai", "based", "sol", "eth", "bsc"]

def is_new_project(address: str) -> bool:
    if not address:
        return False
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM seen_projects WHERE address = ?",
        (address,)
    ).fetchone()
    conn.close()
    return row is None

def mark_as_seen(address: str, chain: str):
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
                pairs = data.get("pairs", [])[:20]
                
                now = datetime.now(timezone.utc)
                results = []
                for pair in pairs:
                    created_at = pair.get("pairCreatedAt")
                    if not created_at:
                        continue
                    
                    created = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
                    age_minutes = (now - created).total_seconds() / 60
                    
                    if age_minutes > 60:  # 1 hour window
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
                    mc = pair.get("marketCap", 0)
                    
                    # Socials
                    twitter = None
                    telegram = None
                    website = None
                    
                    info = pair.get("info", {})
                    socials = info.get("socials", [])
                    for s in socials:
                        s_type = s.get("type", "").lower()
                        if s_type == "twitter":
                            twitter = s.get("url")
                        elif s_type == "telegram":
                            telegram = s.get("url")
                        elif s_type == "website":
                            website = s.get("url")
                    
                    urls = info.get("urls", [])
                    for u in urls:
                        url_str = u.get("url", u) if isinstance(u, dict) else u
                        if "twitter.com" in str(url_str) and not twitter:
                            twitter = url_str
                        elif "t.me" in str(url_str) and not telegram:
                            telegram = url_str
                    
                    results.append({
                        "name": token.get("name", "Unknown"),
                        "symbol": token.get("symbol", "Unknown"),
                        "address": address,
                        "chain": chain,
                        "price": price,
                        "liquidity": liquidity,
                        "volume": volume,
                        "fdv": fdv,
                        "mc": mc,
                        "twitter": twitter,
                        "telegram": telegram,
                        "website": website,
                        "url": f"https://dexscreener.com/{chain}/{pair.get('pairAddress', '')}",
                        "age_minutes": round(age_minutes, 1),
                        "source": "DexScreener"
                    })
                return results
    except Exception as e:
        logger.error(f"Search error for '{query}': {e}")
        return []

async def get_pump_fun() -> List[Dict]:
    """Fetch from Pump.fun"""
    url = LAUNCHPADS["pump.fun"]["url"]
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
                for t in tokens[:40]:
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
                    
                    if age_minutes > 60:
                        continue
                    
                    twitter = t.get("twitter", t.get("twitter_link"))
                    telegram = t.get("telegram", t.get("telegram_link"))
                    website = t.get("website", t.get("website_link"))
                    
                    results.append({
                        "name": t.get("name", "Unknown"),
                        "symbol": t.get("symbol", "Unknown"),
                        "address": address,
                        "chain": "solana",
                        "price": t.get("usd_market_cap", 0),
                        "liquidity": t.get("liquidity", 0),
                        "volume": t.get("usd_volume_24h", 0),
                        "fdv": t.get("usd_market_cap", 0),
                        "mc": t.get("market_cap", 0),
                        "twitter": twitter,
                        "telegram": telegram,
                        "website": website,
                        "url": f"https://pump.fun/coin/{address}",
                        "age_minutes": round(age_minutes, 1),
                        "source": "Pump.fun"
                    })
                return results
    except Exception as e:
        logger.error(f"Pump.fun error: {e}")
        return []

async def get_launchpad(launchpad_name: str, config: dict) -> List[Dict]:
    """Generic launchpad fetcher"""
    url = config["url"]
    chain = config["chain"]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                tokens = data if isinstance(data, list) else data.get("coins", data.get("data", data.get("tokens", [])))
                
                now = datetime.now(timezone.utc)
                results = []
                for t in tokens[:30]:
                    address = t.get("address", t.get("mint", t.get("token_address", t.get("contract", ""))))
                    
                    if not is_new_project(address):
                        continue
                    
                    created_at = t.get("created_at", t.get("created", t.get("timestamp", 0)))
                    if isinstance(created_at, str):
                        try:
                            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        except:
                            created = now - timedelta(hours=2)
                    else:
                        created = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
                    
                    age_minutes = (now - created).total_seconds() / 60
                    
                    if age_minutes > 120:  # 2 hour window for smaller launchpads
                        continue
                    
                    twitter = t.get("twitter", t.get("twitter_link", t.get("social_twitter")))
                    telegram = t.get("telegram", t.get("telegram_link", t.get("social_telegram")))
                    website = t.get("website", t.get("website_link"))
                    
                    results.append({
                        "name": t.get("name", "Unknown"),
                        "symbol": t.get("symbol", "Unknown"),
                        "address": address,
                        "chain": chain,
                        "price": t.get("price", t.get("usd_price", 0)),
                        "liquidity": t.get("liquidity", 0),
                        "volume": t.get("volume_24h", 0),
                        "fdv": t.get("market_cap", t.get("fdv", 0)),
                        "mc": t.get("market_cap", 0),
                        "twitter": twitter,
                        "telegram": telegram,
                        "website": website,
                        "url": t.get("url", f"https://{launchpad_name}"),
                        "age_minutes": round(age_minutes, 1),
                        "source": launchpad_name.capitalize()
                    })
                return results
    except Exception as e:
        logger.error(f"{launchpad_name} error: {e}")
        return []

async def get_moonshot_tokens() -> List[Dict]:
    """Moonshot (Solana launchpad)"""
    try:
        return await get_launchpad("moonshot", LAUNCHPADS["moonshot"])
    except:
        # Fallback: try DexScreener for moonshot tokens
        return await search_new_tokens("moonshot")

async def get_four_meme_tokens() -> List[Dict]:
    """Four.meme (BSC launchpad)"""
    try:
        return await get_launchpad("four.meme", LAUNCHPADS["four.meme"])
    except:
        return []

async def get_sunpump_tokens() -> List[Dict]:
    """SunPump (TRON launchpad)"""
    try:
        return await get_launchpad("sunpump", LAUNCHPADS["sunpump"])
    except:
        return []

async def scan_launchpads(bot: Bot):
    """Main scanner - check ALL sources"""
    logger.info("🔍 Scanning ALL launchpads for new projects...")
    
    all_projects = []
    
    # 1. Pump.fun (largest source)
    pf_tokens = await get_pump_fun()
    if pf_tokens:
        logger.info(f"Pump.fun: {len(pf_tokens)} new")
        all_projects.extend(pf_tokens)
    
    # 2. DexScreener search
    for term in SEARCH_TERMS:
        results = await search_new_tokens(term)
        all_projects.extend(results)
        await asyncio.sleep(0.3)
    
    # 3. Moonshot
    ms = await get_moonshot_tokens()
    if ms:
        logger.info(f"Moonshot: {len(ms)} new")
        all_projects.extend(ms)
    
    # 4. Four.meme
    fm = await get_four_meme_tokens()
    if fm:
        logger.info(f"Four.meme: {len(fm)} new")
        all_projects.extend(fm)
    
    # 5. SunPump
    sp = await get_sunpump_tokens()
    if sp:
        logger.info(f"SunPump: {len(sp)} new")
        all_projects.extend(sp)
    
    # Deduplicate
    seen = set()
    unique = []
    for p in all_projects:
        addr = p.get("address", "")
        if addr and addr not in seen:
            seen.add(addr)
            unique.append(p)
    
    if not unique:
        logger.info("No new projects found.")
        return
    
    # Sort newest first
    unique.sort(key=lambda x: x.get("age_minutes", 999))
    
    # Send alerts (max 8 per scan)
    alerted = 0
    for proj in unique[:8]:
        text = f"🆕 <b>NEW LAUNCH</b>\n\n"
        text += f"📛 <b>{proj['name']}</b> (${proj.get('symbol', 'N/A')})\n"
        text += f"⛓️ Chain: <b>{proj.get('chain', '?').upper()}</b>\n"
        text += f"📡 Source: <b>{proj.get('source', 'Unknown')}</b>\n"
        text += f"⏱️ Age: <b>{proj.get('age_minutes', '?')} min</b>\n"
        text += f"📦 {proj['address'][:8]}...{proj['address'][-6:]}\n"
        
        if proj.get("price") and float(proj.get("price", 0)) > 0:
            text += f"💵 Price: ${float(proj['price']):.8f}\n"
        if proj.get("liquidity") and float(proj.get("liquidity", 0)) > 0:
            text += f"💧 Liq: ${float(proj['liquidity']):,.0f}\n"
        if proj.get("mc") and float(proj.get("mc", 0)) > 0:
            text += f"🏛 MC: ${float(proj['mc']):,.0f}\n"
        if proj.get("volume") and float(proj.get("volume", 0)) > 0:
            text += f"📈 24h Vol: ${float(proj['volume']):,.0f}\n"
        
        links = []
        if proj.get("twitter"):
            links.append(f"🐦 <a href='{proj['twitter']}'>X</a>")
        if proj.get("telegram"):
            links.append(f"📢 <a href='{proj['telegram']}'>TG</a>")
        if proj.get("website"):
            links.append(f"🌐 <a href='{proj['website']}'>Web</a>")
        if proj.get("url"):
            links.append(f"📊 <a href='{proj['url']}'>Chart</a>")
        
        if links:
            text += "  ".join(links)
        
        try:
            await bot.send_message(settings.ADMIN_ID, text, disable_web_page_preview=True)
            mark_as_seen(proj["address"], proj["chain"])
            alerted += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Send error for {proj['name']}: {e}")
    
    logger.info(f"✅ Sent {alerted} launch alerts ({len(unique)} total new)")