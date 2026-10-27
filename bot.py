# Facebook (va Instagram) videolarini yuklab beruvchi Telegram bot
import os
import re
import sys
import uuid
import asyncio
import logging

import yt_dlp
import imageio_ffmpeg
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger("fbbot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "downloads")
MAX_SIZE = 50 * 1024 * 1024  # Telegram bot API cheklovi

URL_REGEX = re.compile(
    r"https?://(?:[a-z0-9-]+\.)?(?:facebook\.com|fb\.watch|fb\.com|instagram\.com)/\S+",
    re.IGNORECASE,
)

dp = Dispatcher()


def download_video(url: str) -> str:
    """Videoni yt-dlp orqali yuklab, fayl yo'lini qaytaradi."""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    outtmpl = os.path.join(DOWNLOADS_DIR, f"{uuid.uuid4().hex}.%(ext)s")
    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "best[ext=mp4][filesize<50M]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "max_filesize": MAX_SIZE,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info and info.get("entries"):
            info = info["entries"][0]
        path = ydl.prepare_filename(info)
    base, _ = os.path.splitext(path)
    for candidate in (path, base + ".mp4"):
        if os.path.exists(candidate):
            return candidate
    raise ValueError("Video fayli topilmadi")


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Assalomu alaykum! Menga Facebook yoki Instagram video havolasini yuboring, "
        "men videoni yuklab beraman."
    )


@dp.message(F.text)
async def handle_link(message: types.Message):
    match = URL_REGEX.search(message.text or "")
    if not match:
        await message.answer("Iltimos, Facebook yoki Instagram video havolasini yuboring.")
        return

    status = await message.answer("Video yuklanmoqda, biroz kuting...")
    path = None
    try:
        path = await asyncio.to_thread(download_video, match.group(0))
        if os.path.getsize(path) > MAX_SIZE:
            await status.edit_text("Video 50 MB dan katta, Telegram orqali yuborib bo'lmaydi.")
            return
        await message.answer_video(FSInputFile(path), supports_streaming=True)
        await status.delete()
    except Exception as e:
        logger.warning("Yuklashda xatolik (%s): %s", match.group(0), e)
        await status.edit_text(
            "Videoni yuklab bo'lmadi. Havola ochiq (public) videoga tegishli ekanini tekshiring."
        )
    finally:
        if path and os.path.exists(path):
            os.remove(path)


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN o'rnatilmagan")
        sys.exit(1)
    bot = Bot(BOT_TOKEN)
    me = await bot.get_me()
    logger.info("Bot ishga tushdi: @%s", me.username)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
