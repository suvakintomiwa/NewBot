from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Alpha", callback_data="cmd_alpha"),
         InlineKeyboardButton(text="📈 Trending", callback_data="cmd_trending")],
        [InlineKeyboardButton(text="💼 Jobs", callback_data="cmd_jobs"),
         InlineKeyboardButton(text="🐸 Memecoins", callback_data="cmd_memecoins")],
        [InlineKeyboardButton(text="📋 Watchlist", callback_data="cmd_watchlist"),
         InlineKeyboardButton(text="🧠 AI", callback_data="cmd_ai")]
    ])
