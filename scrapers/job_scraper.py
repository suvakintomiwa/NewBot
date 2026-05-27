import aiohttp
from bs4 import BeautifulSoup
from loguru import logger
from typing import List, Dict, Any

JOB_SITES = [
    "https://web3.career/",
    "https://cryptojobslist.com/",
    "https://cryptocurrencyjobs.co/"
]

async def fetch_web3_jobs() -> List[Dict[str, Any]]:
    jobs = []
    for site in JOB_SITES:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(site, timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        listings = soup.find_all("div", class_=lambda x: x and "job" in x.lower())
                        for item in listings[:3]:
                            title_tag = item.find(["h2", "h3", "a"])
                            link_tag = item.find("a", href=True)
                            title = title_tag.get_text(strip=True) if title_tag else "Job"
                            link = link_tag["href"] if link_tag else ""
                            if not link.startswith("http"):
                                link = site.rstrip("/") + "/" + link.lstrip("/")
                            jobs.append({"title": title, "company": "Web3", "link": link, "source": site})
        except Exception as e:
            logger.error(f"Job scrape error {site}: {e}")
    return jobs

async def fetch_cm_jobs() -> List[Dict[str, Any]]:
    all_jobs = await fetch_web3_jobs()
    cm_keywords = ["community manager", "cm", "community lead", "moderator"]
    return [j for j in all_jobs if any(k in j['title'].lower() for k in cm_keywords)]

async def fetch_mod_jobs() -> List[Dict[str, Any]]:
    all_jobs = await fetch_web3_jobs()
    mod_keywords = ["moderator", "mod", "discord mod", "telegram mod"]
    return [j for j in all_jobs if any(k in j['title'].lower() for k in mod_keywords)]
