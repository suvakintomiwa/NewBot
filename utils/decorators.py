from functools import wraps
from aiogram import types
from config.settings import settings

def admin_only(func):
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        if message.from_user.id != settings.ADMIN_ID:
            await message.answer("⛔ Access denied. This bot is private.")
            return
        return await func(message, *args, **kwargs)
    return wrapper
