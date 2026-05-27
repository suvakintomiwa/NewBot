from aiogram import Router, types
from aiogram.filters import Command
from utils.decorators import admin_only
from database.db import get_connection

router = Router()

@router.message(Command("watchlist"))
@admin_only
async def cmd_watchlist(message: types.Message):
    conn = get_connection()
    rows = conn.execute("SELECT symbol, name, chain FROM watchlist WHERE user_id = ?", (message.from_user.id,)).fetchall()
    if not rows:
        await message.answer("📋 Your watchlist is empty. Use /save to add.")
        return
    text = "<b>⭐ WATCHLIST</b>\n"
    for r in rows:
        text += f"• {r['symbol']} ({r['name']}) - {r['chain']}\n"
    await message.answer(text)

@router.message(Command("save"))
@admin_only
async def cmd_save(message: types.Message):
    args = message.text.split(maxsplit=3)
    if len(args) < 3:
        await message.answer("Usage: /save <symbol> <name> [chain]")
        return
    symbol = args[1].upper()
    name = args[2]
    chain = args[3] if len(args) > 3 else "ETH"
    conn = get_connection()
    conn.execute("INSERT INTO watchlist (user_id, token_id, symbol, name, chain) VALUES (?,?,?,?,?)",
                 (message.from_user.id, symbol, symbol, name, chain))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Added {symbol} to watchlist.")
