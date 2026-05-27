from aiogram import Router, types
from aiogram.filters import Command
from utils.decorators import admin_only
from scrapers.job_scraper import fetch_web3_jobs, fetch_cm_jobs, fetch_mod_jobs
import random

router = Router()

@router.message(Command("jobs"))
@admin_only
async def cmd_jobs(message: types.Message):
    await message.answer("💼 Fetching Web3 jobs...")
    jobs = await fetch_web3_jobs()
    if not jobs:
        await message.answer("No jobs found.")
        return
    random.shuffle(jobs)
    for job in jobs[:5]:
        await message.answer(f"<b>{job['title']}</b>\n{job['company']}\n{job['link']}", disable_web_page_preview=True)

@router.message(Command("cmjobs"))
@admin_only
async def cmd_cmjobs(message: types.Message):
    await message.answer("🧑‍🤝‍🧑 Community manager jobs...")
    jobs = await fetch_cm_jobs()
    if not jobs:
        await message.answer("No CM jobs.")
        return
    for job in jobs[:5]:
        await message.answer(f"<b>{job['title']}</b>\n{job['link']}", disable_web_page_preview=True)

@router.message(Command("modjobs"))
@admin_only
async def cmd_modjobs(message: types.Message):
    await message.answer("🛡️ Moderator jobs...")
    jobs = await fetch_mod_jobs()
    if not jobs:
        await message.answer("No mod jobs.")
        return
    for job in jobs[:5]:
        await message.answer(f"<b>{job['title']}</b>\n{job['link']}", disable_web_page_preview=True)

@router.message(Command("nftjobs"))
@admin_only
async def cmd_nftjobs(message: types.Message):
    await message.answer("🎨 NFT artist/creator gigs coming soon.")

@router.message(Command("tester"))
@admin_only
async def cmd_tester(message: types.Message):
    await message.answer("🧪 Tester/bug bounty opportunities will be listed here.")
