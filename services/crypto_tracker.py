from scrapers.crypto_scraper import get_coingecko_trending

async def get_trending():
    return await get_coingecko_trending()

async def get_memecoins():
    trending = await get_coingecko_trending()
    return trending[:5]  # placeholder

async def get_new_projects():
    return []
