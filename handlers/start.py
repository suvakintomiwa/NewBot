from aiogram import Router, types
from aiogram.filters import Command
from utils.decorators import admin_only

router = Router()

@router.message(Command("start"))
@admin_only
async def cmd_start(message: types.Message):
    welcome_text = (
        "⚡ <b>Web3 Jarvis Online</b> ⚡\n\n"
        "I'm your elite Web3 AI assistant. Commands:\n"
        "/ai &lt;query&gt; – ask anything\n"
        "/alpha – crypto alpha feed\n"
        "/trending – trending coins\n"
        "/memecoins – meme coin radar\n"
        "/newprojects – fresh launches\n"
        "/jobs – web3 job listings\n"
        "/cmjobs – community manager jobs\n"
        "/modjobs – moderator jobs\n"
        "/watchlist – manage token watchlist\n"
        "/save – save project\n"
        "/notes – add quick notes\n"
        "/reminder – set reminders\n"
        "/analyze – analyze project/contract\n"
        "/outreach – generate outreach DM\n"
        "/raid – raid message generator\n"
        "/shill – shill post generator\n"
        "/briefing – daily briefing\n"
    )
    await message.answer(welcome_text)
