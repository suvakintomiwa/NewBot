from aiogram import Router, types
from aiogram.filters import Command
from utils.decorators import admin_only
from scrapers.crypto_scraper import search_contract

router = Router()

@router.message(Command("checkproject"))
@admin_only
async def cmd_checkproject(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /checkproject <token contract>")
        return
    contract = args[1].strip()
    await message.answer("🔎 Checking project...")
    data = await search_contract(contract)
    if not data:
        await message.answer("Could not fetch data.")
        return
    text = f"<b>📋 {data.get('name', 'Unknown')} ({data.get('symbol', '')})</b>\n"
    text += f"• Price: ${data.get('price', 'N/A')}\n"
    text += f"• 24h Change: {data.get('change', 'N/A')}%\n"
    text += f"• FDV: ${data.get('fdv', 'N/A')}\n"
    text += f"• Liquidity: ${data.get('liquidity', 'N/A')}\n"
    text += f"\n🔗 <a href='{data.get('url', '')}'>DexScreener</a>"
    await message.answer(text, disable_web_page_preview=True)

@router.message(Command("solana"))
@admin_only
async def cmd_solana(message: types.Message):
    await message.answer("🟣 Solana ecosystem alpha coming soon.")

@router.message(Command("base"))
@admin_only
async def cmd_base(message: types.Message):
    await message.answer("🔵 Base ecosystem trends will appear here.")

@router.message(Command("eth"))
@admin_only
async def cmd_eth(message: types.Message):
    await message.answer("Ξ Ethereum ecosystem overview on the way.")
