import os
import sys
from dotenv import load_dotenv

# .env faylini yuklaymiz
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Yuklab olinadigan vaqtinchalik papka
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "downloads")

# Google Gemini AI konfiguratsiyasi
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# Majburiy kanal obunasi (masalan: @kanalingiz yoki ID)
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "").strip()
CHANNEL_URL = os.getenv("CHANNEL_URL", "").strip()

# Bot egasi / Admin ID si
ADMIN_ID = os.getenv("ADMIN_ID", "1722855035").strip()

# Ommaviy rejim (True bo'lsa barcha foydalanuvchilar kira oladi, False bo'lsa faqat Admin)
PUBLIC_MODE = os.getenv("PUBLIC_MODE", "true").lower() in ("true", "1", "yes")

# Wi-Fi avtomatik belgilash uchun mahalliy server porti
WIFI_PORT = int(os.getenv("WIFI_PORT", "8088"))

# Shaxsiy Telegram guruh sozlamalari (hujjatlarni avtomat yo'naltirish uchun)
GROUP_ID = os.getenv("GROUP_ID", "").strip()
DOCS_TOPIC_ID = os.getenv("DOCS_TOPIC_ID", "").strip()

# Foydalanuvchi o'zi qo'yishi mumkin bo'lgan stikerlar / emojilar
# Bo'sh qoldirilsa - stikerlar umuman ko'rinmaydi (minimalistik toza matn)
ICON_WORK_IN = os.getenv("ICON_WORK_IN", "").strip()
ICON_WORK_OUT = os.getenv("ICON_WORK_OUT", "").strip()
ICON_DOCUMENTS = os.getenv("ICON_DOCUMENTS", "").strip()
ICON_REMINDERS = os.getenv("ICON_REMINDERS", "").strip()
ICON_REPORT = os.getenv("ICON_REPORT", "").strip()
ICON_AI = os.getenv("ICON_AI", "").strip()

def validate_config():
    """Bot konfiguratsiyasini tekshiradi."""
    if not BOT_TOKEN or BOT_TOKEN.strip() == "" or BOT_TOKEN == "SIZNING_BOT_TOKENINGIZ":
        print("\n" + "=" * 60, flush=True)
        print("XATOLIK: BOT_TOKEN topilmadi yoki kiritilmagan!", flush=True)
        print("Iltimos, .env faylini oching va Telegram @BotFather dan", flush=True)
        print("olingan tokenni BOT_TOKEN=... qatoriga yozing.", flush=True)
        print("=" * 60 + "\n", flush=True)
        sys.exit(1)

