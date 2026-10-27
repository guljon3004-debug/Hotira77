# Railway'da 24/7 ishga tushirish

1. https://railway.com ga GitHub orqali kiring → **New Project** → **Deploy from GitHub repo** → `Hotira77` ni tanlang (sozlamalar `railway.json` da tayyor).
2. Servis ichida **Variables** bo'limiga quyidagilarni qo'shing (tokenlarni hech qachon git'ga yozmang):
   - `BOT_TOKEN` — @BotFather tokeni
   - `ADMIN_ID` — sizning Telegram ID
   - `GEMINI_API_KEY` — Gemini kaliti
   - `DATA_DIR` = `/data`
3. Servisni o'ng tugma bilan bosing → **Attach Volume** → Mount path: `/data`. Baza (`vault.db`) va saqlangan fayllar shu yerda turadi va qayta deploy'da o'chmaydi.
4. **Deploy** ni bosing. **Deployments → Logs** da "Hotira77 boti muvaffaqiyatli ishga tushdi" yozuvi chiqishi kerak.

Muhim: botni bir vaqtda faqat bitta joyda ishlating (kompyuterdagi botni o'chiring), aks holda Telegram `Conflict` xatosini beradi.

Eski bazani ko'chirish uchun kompyuterdagi `vault.db` faylini volume'ga yuklash mumkin (Railway CLI: `railway ssh` yoki `railway volume`).
