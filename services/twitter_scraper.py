import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from loguru import logger
from config.settings import settings
from aiogram import Bot
from database.db import get_connection
from typing import List, Dict
import asyncio
import random

NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.poast.org",
    "https://nitter.unixfox.eu",
]

HASHTAGS = [
    "memecoin", "crypto", "Solana", "1000x", "gem", "airdrop",
    "NFT", "DeFi", "Web3", "altcoin", "BTC", "ETH", "pump",
    "meme", "pepe", "doge", "wojak", "newlaunch", "fairlaunch",
    "presale", "whitelist", "trading", "based"
]

def is_new_tweet(tweet_id: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT id FROM seen_tweets WHERE tweet_id = ?", (tweet_id,)).fetchone()
    conn.close()
    return row is None

def mark_tweet_seen(tweet_id: str):
    conn = get_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO seen_tweets (tweet_id) VALUES (?)", (tweet_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"DB tweet error: {e}")
    finally:
        conn.close()

async def search_nitter_hashtag(hashtag: str) -> List[Dict]:
    nitter = random.choice(NITTER_INSTANCES)
    url = f"{nitter}/search?f=tweets&q=%23{hashtag}&since=1h"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                tweets = []
                items = soup.find_all("div", class_="timeline-item")
                
                for item in items[:10]:
                    try:
                        link_tag = item.find("a", class_="tweet-link")
                        if not link_tag:
                            continue
                        
                        tweet_url = link_tag.get("href", "")
                        tweet_id = tweet_url.split("/")[-1].split("#")[0]
                        
                        if not tweet_id or not is_new_tweet(tweet_id):
                            continue
                        
                        user_tag = item.find("a", class_="username")
                        username = user_tag.text.strip() if user_tag else "Unknown"
                        
                        content_tag = item.find("div", class_="tweet-content")
                        content = content_tag.text.strip()[:300] if content_tag else ""
                        
                        stats = item.find_all("span", class_="tweet-stat")
                        likes = retweets = comments = 0
                        for stat in stats:
                            text = stat.text.strip()
                            icon = stat.find("i")
                            if icon:
                                classes = str(icon.get("class", ""))
                                num = int(''.join(filter(str.isdigit, text)) or 0)
                                if "heart" in classes:
                                    likes = num
                                elif "retweet" in classes:
                                    retweets = num
                                elif "comment" in classes:
                                    comments = num
                        
                        time_tag = item.find("span", class_="tweet-date")
                        post_time = time_tag.find("a").text.strip() if time_tag and time_tag.find("a") else "recent"
                        
                        tweets.append({
                            "tweet_id": tweet_id,
                            "username": username,
                            "content": content,
                            "likes": likes,
                            "retweets": retweets,
                            "comments": comments,
                            "time": post_time,
                            "url": f"https://twitter.com{link_tag.get('href', '')}" if tweet_url.startswith("/") else tweet_url,
                            "hashtag": hashtag
                        })
                    except:
                        continue
                return tweets
    except Exception as e:
        logger.error(f"Nitter error for #{hashtag}: {e}")
        return []

async def scan_twitter(bot: Bot):
    logger.info("🐦 Scanning X/Twitter...")
    
    all_tweets = []
    selected = random.sample(HASHTAGS, min(10, len(HASHTAGS)))
    
    for tag in selected:
        tweets = await search_nitter_hashtag(tag)
        if tweets:
            # Only high-engagement tweets
            good = [t for t in tweets if t["likes"] > 5 or t["retweets"] > 2]
            all_tweets.extend(good[:2] if good else tweets[:1])
        await asyncio.sleep(0.5)
    
    if not all_tweets:
        return
    
    # Deduplicate & sort by engagement
    seen_ids = set()
    unique = []
    for t in all_tweets:
        tid = t["tweet_id"]
        if tid not in seen_ids and is_new_tweet(tid):
            seen_ids.add(tid)
            unique.append(t)
    
    unique.sort(key=lambda x: x["likes"] + x["retweets"], reverse=True)
    
    for tweet in unique[:5]:
        text = f"🐦 <b>CRYPTO TWEET</b>\n\n"
        text += f"👤 @{tweet['username']}\n"
        text += f"💬 {tweet['content'][:200]}\n\n"
        text += f"❤️ {tweet['likes']} | 🔄 {tweet['retweets']} | 💬 {tweet['comments']}\n"
        text += f"🕐 {tweet['time']} | #{tweet['hashtag']}\n"
        text += f"🔗 <a href='{tweet['url']}'>View on X</a>"
        
        try:
            await bot.send_message(settings.ADMIN_ID, text, disable_web_page_preview=True)
            mark_tweet_seen(tweet["tweet_id"])
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Tweet send error: {e}")
    
    logger.info(f"🐦 Sent {min(len(unique), 5)} tweet alerts")