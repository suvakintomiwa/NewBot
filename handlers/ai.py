from aiogram import Router, types
from aiogram.filters import Command
from utils.decorators import admin_only
from services.ai_manager import ai_response

router = Router()

@router.message(Command("ai"))
@admin_only
async def cmd_ai(message: types.Message):
    prompt = message.text.partition(" ")[2]
    if not prompt:
        await message.answer("🔮 Send me a question, e.g., <code>/ai what is the best Web3 outreach strategy?</code>")
        return
    await message.answer("🤖 Thinking...")
    try:
        reply = await ai_response(prompt, user_id=message.from_user.id)
        await message.answer(reply, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ AI error: {str(e)[:200]}")
