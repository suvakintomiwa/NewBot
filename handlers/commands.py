from aiogram import Router, types
from aiogram.filters import Command
from utils.decorators import admin_only
from services.crypto_tracker import get_trending, get_memecoins, get_new_projects
from services.ai_manager import ai_response

router = Router()

@router.message(Command("help"))
@admin_only
async def cmd_help(message: types.Message):
    await message.answer("Refer to /start for full command list.")

@router.message(Command("alpha"))
@admin_only
async def cmd_alpha(message: types.Message):
    await message.answer("🔭 Scanning alpha...")
    data = await get_trending()
    if not data:
        await message.answer("No alpha found at the moment.")
        return
    text = "<b>🔥 ALPHA FEED</b>\n"
    for coin in data[:5]:
        text += f"• {coin['symbol']} (+{coin['change']}%) | {coin['name']}\n"
    await message.answer(text)

@router.message(Command("trending"))
@admin_only
async def cmd_trending(message: types.Message):
    data = await get_trending()
    if not data:
        await message.answer("No trending data.")
        return
    text = "<b>🚀 TRENDING</b>\n"
    for coin in data[:10]:
        text += f"• <b>{coin['symbol']}</b> ${coin.get('price', 'N/A')} ({coin.get('change_24h', 'N/A')}%)\n"
    await message.answer(text)

@router.message(Command("memecoins"))
@admin_only
async def cmd_memecoins(message: types.Message):
    data = await get_memecoins()
    if not data:
        await message.answer("No meme coin data.")
        return
    text = "<b>🐸 MEMECOIN RADAR</b>\n"
    for token in data[:10]:
        text += f"• {token['name']} ({token['symbol']}) | Vol: ${token.get('volume', 'N/A')}\n"
    await message.answer(text)

@router.message(Command("newprojects"))
@admin_only
async def cmd_newprojects(message: types.Message):
    data = await get_new_projects()
    if not data:
        await message.answer("No new launches.")
        return
    text = "<b>🆕 NEW LAUNCHES</b>\n"
    for proj in data[:5]:
        text += f"• <b>{proj['name']}</b> ({proj['chain']})\n"
    await message.answer(text)

@router.message(Command("briefing"))
@admin_only
async def cmd_briefing(message: types.Message):
    await message.answer("📊 Generating daily briefing...")
    trending = await get_trending()
    prompt = f"Create a short daily Web3 briefing with trending coins: {trending[:3]}. Include alpha tips."
    reply = await ai_response(prompt, user_id=message.from_user.id)
    await message.answer(f"<b>🗞️ DAILY BRIEFING</b>\n{reply}")

@router.message(Command("analyze"))
@admin_only
async def cmd_analyze(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /analyze <contract/url>")
        return
    target = args[1]
    await message.answer("🔍 Analyzing...")
    prompt = f"Analyze this Web3 project: {target}. Give trust score, risk score, alpha score out of 10, and brief summary."
    analysis = await ai_response(prompt, user_id=message.from_user.id)
    await message.answer(f"<b>📊 PROJECT ANALYSIS</b>\n\n{analysis}")
