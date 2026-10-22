# 🧠 Hotira77 — Shaxsiy Xotira, Eslatmalar va Jonli Radar Telegram Boti

Ushbu bot **Python**, **Aiogram 3**, **SQLite**, **Edge TTS** va **Google Gemini AI** texnologiyalari asosida yaratilgan shaxsiy xotira va eslatmalar yordamchisidir.

* **Telegram Bot:** [@Hotira77_bot](https://t.me/Hotira77_bot)

---

## 🌟 Asosiy imkoniyatlari

### 1. 📍 Jonli Ko'chalar Radari (Live Location Voice Radar)
- Telegram **Live Location** (Jonli joylashuv) orqali harakatni real vaqtda kuzatish.
- OpenStreetMap / Nominatim orqali joriy ko'cha nomini avtomatik aniqlash.
- Yangi ko'chaga o'tganda yoqimli o'zbekcha ayol ovozi (**Madina Neural**) orqali ovozli xabar berish.

### 2. ⏰ Aqlli Eslatmalar (Reminders & Tasks)
- Tabiiy tildagi vaqtli eslatmalar (masalan, *«Ertaga 10:00 da hisobot topshirish»* yoki *«16:30 da uchrashuv»*).
- Belgilangan vaqtda Telegram orqali xabar berish.
- Bajarildi / Qoldirish tugmalari.

### 3. 📁 Shaxsiy Seyf va Hujjatlar Ombori
- Muhim hujjatlar, qaydlar va shaxsiy fayllarni xavfsiz saqlash.
- Nomi bo'yicha tezkor qidirish va istalgan vaqtda qayta yuklab olish.

### 4. 🤖 Google Gemini AI Suhbatdosh
- Savollarga tezkor va ravon o'zbek tilida javob beruvchi sun'iy intellekt.
- Ovozli va matnli rejim.

---

## 🚀 O'rnatish va Ishga tushirish

1. **Repozitoriyani yuklab olish:**
`ash
git clone https://github.com/guljon3004-debug/Hotira77.git
cd Hotira77
`

2. **Kutubxonalarni o'rnatish:**
`ash
pip install -r requirements.txt
`

3. **.env faylini sozlash:**
.env.example faylidan nusxa olib .env yarating:
`env
BOT_TOKEN=telegram_bot_token
ADMIN_ID=admin_telegram_id
GEMINI_API_KEY=gemini_api_key
GEMINI_MODEL=gemini-flash-latest
`

4. **Ishga tushirish:**
`ash
python bot.py
`
yoki Windows tizimida start.bat faylini ishga tushiring.
