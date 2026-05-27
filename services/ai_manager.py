import asyncio
import aiohttp
from loguru import logger
from config.settings import settings
from typing import Optional

PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": settings.GROQ_API_KEY,
        "model": "llama3-8b-8192"
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key": settings.OPENROUTER_API_KEY,
        "model": "meta-llama/llama-3-8b-instruct:free"
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
        "key": settings.GEMINI_API_KEY,
        "model": "gemini-pro"
    },
    "deepseek": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "key": settings.DEEPSEEK_API_KEY,
        "model": "deepseek-chat"
    }
}

FALLBACK_ORDER = ["groq", "openrouter", "gemini", "deepseek"]

async def ai_response(prompt: str, user_id: int, history: list = None) -> str:
    for provider_name in FALLBACK_ORDER:
        provider = PROVIDERS.get(provider_name)
        if not provider or not provider["key"]:
            continue
        try:
            if provider_name == "gemini":
                reply = await call_gemini(provider, prompt, history)
            else:
                reply = await call_openai_compatible(provider, prompt, history)
            if reply:
                from database.db import get_connection
                conn = get_connection()
                conn.execute("INSERT INTO conversations (user_id, role, content) VALUES (?,?,?)",
                             (user_id, "user", prompt))
                conn.execute("INSERT INTO conversations (user_id, role, content) VALUES (?,?,?)",
                             (user_id, "assistant", reply))
                conn.commit()
                conn.close()
                return reply
        except Exception as e:
            logger.error(f"Provider {provider_name} failed: {e}")
            continue
    return "All AI providers are unavailable. Please try later."

async def call_openai_compatible(provider: dict, prompt: str, history: list = None) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {provider['key']}",
        "Content-Type": "application/json"
    }
    messages = [{"role": "system", "content": "You are a Web3 expert assistant. Give concise, actionable advice."}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": provider["model"],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(provider["url"], headers=headers, json=payload, timeout=30) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"{provider['url']} returned {resp.status}")
                return None

async def call_gemini(provider: dict, prompt: str, history: list = None) -> Optional[str]:
    url = f"{provider['url']}?key={provider['key']}"
    contents = [{"parts": [{"text": prompt}]}]
    payload = {"contents": contents}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, timeout=30) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            else:
                logger.error(f"Gemini API error {resp.status}")
                return None
