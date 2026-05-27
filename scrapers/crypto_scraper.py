import aiohttp
from loguru import logger
from typing import Optional, Dict, Any, List

DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"
COINGECKO_API = "https://api.coingecko.com/api/v3"

async def search_contract(contract_address: str) -> Optional[Dict[str, Any]]:
    url = f"{DEXSCREENER_API}/search?q={contract_address}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])
                    if pairs:
                        pair = pairs[0]
                        return {
                            "name": pair.get("baseToken", {}).get("name", "Unknown"),
                            "symbol": pair.get("baseToken", {}).get("symbol", ""),
                            "price": pair.get("priceUsd"),
                            "change": pair.get("priceChange", {}).get("h24"),
                            "fdv": pair.get("fdv"),
                            "liquidity": pair.get("liquidity", {}).get("usd"),
                            "url": f"https://dexscreener.com/.../{pair.get('chainId','')}/{pair.get('pairAddress','')}"
                        }
    except Exception as e:
        logger.error(f"DexScreener error: {e}")
    return None

async def get_coingecko_trending() -> List[Dict[str, Any]]:
    url = f"{COINGECKO_API}/search/trending"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    coins = data.get("coins", [])
                    result = []
                    for c in coins[:10]:
                        item = c["item"]
                        result.append({
                            "symbol": item["symbol"],
                            "name": item["name"],
                            "price": item.get("price_btc"),
                            "change": item.get("price_change_percentage_24h", {}).get("usd"),
                            "change_24h": item.get("price_change_percentage_24h", {}).get("usd"),
                            "url": f"https://www.coingecko.com/en/coins/{item['id']}"
                        })
                    return result
    except Exception as e:
        logger.error(f"CoinGecko trending error: {e}")
    return []
