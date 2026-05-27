from aiogram import Router, types
from aiogram.filters import Command
from utils.decorators import admin_only
from database.db import get_connection

router = Router()

@router.message(Command("notes"))
@admin_only
async def cmd_notes(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        conn = get_connection()
        rows = conn.execute("SELECT id, content, category, created_at FROM notes WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
                            (message.from_user.id,)).fetchall()
        if not rows:
            await message.answer("📝 No notes.")
            return
        text = "<b>📒 YOUR NOTES</b>\n"
        for r in rows:
            text += f"[{r['category']}] {r['content'][:50]}... ({r['created_at'][:10]})\n"
        await message.answer(text)
    else:
        content = args[1]
        conn = get_connection()
        conn.execute("INSERT INTO notes (user_id, category, content) VALUES (?,?,?)",
                     (message.from_user.id, "general", content))
        conn.commit()
        conn.close()
        await message.answer("🗒️ Note saved.")

@router.message(Command("reminder"))
@admin_only
async def cmd_reminder(message: types.Message):
    await message.answer("⏰ Reminder feature to be implemented with inline scheduling.")
