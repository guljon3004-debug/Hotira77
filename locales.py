# -*- coding: utf-8 -*-
# Hotira77 — Shaxsiy Xotira, Eslatmalar va Jonli Radar Boti

MESSAGES = {
    "uz": {
        "btn_auto_radar": "🚗📍 AVTO-RADAR (Joylashuv)",
        "btn_reminders": "⏰ Eslatmalar",
        "btn_documents": "📁 Shaxsiy Seyf",
        "btn_ai": "🤖 AI Maslahatchi",
        "btn_settings": "⚙️ Sozlamalar",
        "btn_cancel": "❌ Bekor qilish",
        "btn_back_main": "🏠 Asosiy menyu",
        "btn_clear_chat": "🗑 Suhbatni tozalash",

        "start_title": "<b>Xush kelibsiz, {name}! 🌹</b>",
        "start_desc": (
            "<b>HOTIRA77 — SHAXSIY XOTIRA, ESLATMALAR VA JONLI RADAR BOTI</b>\n\n"
            "Ushbu bot faqat shaxsiy ehtiyojlaringiz uchun sozlangan:\n\n"
            "🚗 <b>Jonli Ko'chalar Radari:</b> Harakatlanayotganingizda yangi ko'chaga o'tishingiz bilanoq "
            "bot sizga yoqimli o'zbekcha <i>Madina</i> ovozida aytib turadi.\n"
            "⏰ <b>Aqlli Eslatmalar:</b> Istalgan vaqtli eslatmani yozing (masalan: <i>15 daqiqadan keyin telefon qilish</i>).\n"
            "📁 <b>Shaxsiy Seyf:</b> Istalgan muhim fayl, hujjat, rasm yoki audiolar xavfsiz saqlanadi.\n"
            "🤖 <b>Doimiy Gemini AI:</b> Istalgan savolingizni matn yoki ovozli xabar ko'rinishida yuboring — AI darhol javob beradi."
        ),
        "unauthorized": "⛔ <b>Kirish cheklangan.</b> Ushbu bot faqat uning egasi uchun shaxsiy rejimda ishlaydi.",

        "reminders_title": "<b>⏰ SHAXSIY ESLATMALAR</b>\n\nQuyida sizning faol eslatmalaringiz ro'yxati:",
        "no_reminders": "<i>Hozircha faol eslatmalar yo'q.</i>\n\nYangi eslatma qo'shish uchun quyidagi tugmani bosing yoki to'g'ridan-to'g'ri yozing (masalan: <i>10 daqiqadan keyin choy ichish</i>).",
        "btn_add_rem": "➕ Yangi eslatma qo'shish",
        "btn_done": "✅ Bajarildi",
        "btn_delete": "🗑 O'chirish",
        "btn_snooze": "⏳ 10 daqiqa qoldirish",
        "prompt_rem_text": "<b>Yangi eslatma matnini kiriting:</b>\n(Masalan: <i>Hisobotni tekshirish</i>)",
        "prompt_rem_time": "<b>Eslatma vaqtini kiriting:</b>\n\n<i>Namunalar:</i>\n• <code>15 daqiqa</code> yoki <code>1 soat</code>\n• <code>18:30</code> (bugun)\n• <code>ertaga 09:00</code>\n• <code>25.10 14:00</code>",
        "rem_created": "✅ <b>Eslatma saqlandi!</b>\n\n📝 Matn: {text}\n⏰ Vaqt: <b>{time}</b>",
        "rem_alert": "⏰ <b>ESLATMA VAQTI KELDI!</b>\n\n📌 <b>{text}</b>\n\n<i>Rejangizni bajargan bo'lsangiz «Bajarildi» tugmasini bosing:</i>",
        "rem_done_msg": "✅ Eslatma bajarildi deb belgilandi.",
        "rem_deleted": "🗑 Eslatma o'chirildi.",
        "rem_snoozed": "⏳ Eslatma 10 daqiqaga qoldirildi.",

        "docs_title": "<b>📁 SHAXSIY SEYF (HUJJATLAR VA FAYLLAR)</b>\n\nBu yerda barcha muhim fayllaringiz xavfsiz saqlanadi.",
        "no_docs": "<i>Seyfda hech qanday hujjat yo'q.</i>\n\nIstalgan PDF, Word, Excel, rasm yoki arxiv faylni yuborsangiz, bot uni avtomatik saqlaydi.",
        "doc_saved": "✅ <b>Fayl muvaffaqiyatli saqlandi!</b>\n\n📄 Nomi: <code>{name}</code>\n📦 Hajmi: {size}\n🏷 Tur: {type}",
        "btn_download": "📥 Yuklab olish",

        "radar_info": (
            "<b>🚗📍 JONLI KO'CHALAR RADARI</b>\n\n"
            "Ko'chalarda yurganingizda yangi ko'chaga o'tganingizni avtomatik eshitib borish uchun:\n\n"
            "1. Pastdagi <b>📎 (Qisqich)</b> belgisini bosing;\n"
            "2. <b>📍 Геопозиция (Location)</b> bo'limiga kiring;\n"
            "3. <b>«Транслировать геопозицию» (Jonli geolokatsiya)</b> ni yoqing (masalan, 1 soat yoki 8 soatga).\n\n"
            "<i>Shundan so'ng avtomobilda harakatlanayotganingizda yangi ko'chaga o'tishingiz bilanoq bot o'zbekcha yoqimli ovozda aytib turadi.</i>"
        ),
        "loc_current": "📍 <b>Sizning hozirgi joyingiz:</b>\nKo'cha: <b>{road}</b>\nHudud: {district}\nVaqt: {time}",
        "street_changed_voice": "Siz {old}dan {new}ga o'tdingiz.",

        "ai_title": "<b>🤖 GEMINI AI YORDAMCHI</b>\n\nSiz bot bilan istalgan mavzuda matnli yoki ovozli xabar orqali muloqot qilishingiz mumkin. Savolingizni bemalol yozing!",
        "chat_cleared": "🧹 AI suhbat xotirasi tozalandi. Yangi mavzudan boshlashingiz mumkin.",

        "settings_title": "<b>⚙️ SOZLAMALAR</b>\n\nQuyidagi sozlamalarni o'zgartirishingiz mumkin:",
        "voice_on": "🔊 Ovozli javoblar: <b>YOQILGAN</b>",
        "voice_off": "🔇 Ovozli javoblar: <b>O'CHIRILGAN</b>",
        "btn_toggle_voice": "🔊/🔇 Ovozni yoqish/o'chirish",
        "btn_lang": "🌐 Tilni o'zgartirish"
    },

    "ru": {
        "btn_auto_radar": "🚗📍 АВТО-РАДАР (Геопозиция)",
        "btn_reminders": "⏰ Напоминания",
        "btn_documents": "📁 Личный Сейф",
        "btn_ai": "🤖 AI Помощник",
        "btn_settings": "⚙️ Настройки",
        "btn_cancel": "❌ Отмена",
        "btn_back_main": "🏠 Главное меню",
        "btn_clear_chat": "🗑 Очистить чат",

        "start_title": "<b>Добро пожаловать, {name}! 🌹</b>",
        "start_desc": (
            "<b>HOTIRA77 — ПЕРСОНАЛЬНАЯ ПАМЯТЬ, НАПОМИНАНИЯ И ЖИВОЙ РАДАР</b>\n\n"
            "Бот настроен для ваших персональных задач:\n\n"
            "🚗 <b>Живой Радар Улиц:</b> При движении по городу при переходе на новую улицу "
            "бот автоматически предупреждает приятным узбекским голосом <i>Мадина</i>.\n"
            "⏰ <b>Умные Напоминания:</b> Напоминания на естественном языке (напр.: <i>через 15 минут перезвонить</i>).\n"
            "📁 <b>Личный Сейф:</b> Безопасное хранение важных файлов, документов и фото.\n"
            "🤖 <b>Постоянный Gemini AI:</b> Задавайте любые вопросы текстом или голосовыми — AI мгновенно отвечает."
        ),
        "unauthorized": "⛔ <b>Доступ ограничен.</b> Этот бот работает только для своего владельца.",

        "reminders_title": "<b>⏰ ВАШИ НАПОМИНАНИЯ</b>\n\nСписок активных напоминаний:",
        "no_reminders": "<i>Активных напоминаний нет.</i>\n\nЧтобы добавить, нажмите кнопку ниже или просто напишите (напр.: <i>через 10 минут чай</i>).",
        "btn_add_rem": "➕ Добавить напоминание",
        "btn_done": "✅ Выполнено",
        "btn_delete": "🗑 Удалить",
        "btn_snooze": "⏳ Отложить на 10 мин",
        "prompt_rem_text": "<b>Введите текст напоминания:</b>\n(Например: <i>Проверить отчет</i>)",
        "prompt_rem_time": "<b>Введите время напоминания:</b>\n\n<i>Примеры:</i>\n• <code>15 минут</code> или <code>1 час</code>\n• <code>18:30</code> (сегодня)\n• <code>завтра 09:00</code>\n• <code>25.10 14:00</code>",
        "rem_created": "✅ <b>Напоминание сохранено!</b>\n\n📝 Текст: {text}\n⏰ Время: <b>{time}</b>",
        "rem_alert": "⏰ <b>ВРЕМЯ НАПОМИНАНИЯ!</b>\n\n📌 <b>{text}</b>",
        "rem_done_msg": "✅ Отмечено как выполненное.",
        "rem_deleted": "🗑 Напоминание удалено.",
        "rem_snoozed": "⏳ Напоминание отложено на 10 минут.",

        "docs_title": "<b>📁 ЛИЧНЫЙ СЕЙФ (ДОКУМЕНТЫ И ФАЙЛЫ)</b>\n\nЗдесь безопасно хранятся все ваши файлы.",
        "no_docs": "<i>В сейфе нет файлов.</i>\n\nОтправьте любой PDF, Word, Excel, фото или архив, и бот сохранит его.",
        "doc_saved": "✅ <b>Файл успешно сохранен!</b>\n\n📄 Имя: <code>{name}</code>\n📦 Размер: {size}\n🏷 Тип: {type}",
        "btn_download": "📥 Скачать",

        "radar_info": (
            "<b>🚗📍 ЖИВОЙ РАДАР УЛИЦ</b>\n\n"
            "Чтобы слышать голосовые оповещения о смене улиц при движении:\n\n"
            "1. Нажмите скрепку <b>📎</b> внизу;\n"
            "2. Выберите <b>📍 Геопозиция (Location)</b>;\n"
            "3. Включите <b>«Транслировать геопозицию»</b> (на 1 или 8 часов).\n\n"
            "<i>Бот будет озвучивать смену улиц голосом в реальном времени.</i>"
        ),
        "loc_current": "📍 <b>Текущее местоположение:</b>\nУлица: <b>{road}</b>\nРайон: {district}\nВремя: {time}",
        "street_changed_voice": "Вы переехали с {old} на {new}.",

        "ai_title": "<b>🤖 GEMINI AI ПОМОЩНИК</b>\n\nОбщайтесь с искусственным интеллектом голосом или текстом в любое время!",
        "chat_cleared": "🧹 Контекст чата очищен.",

        "settings_title": "<b>⚙️ НАСТРОЙКИ</b>",
        "voice_on": "🔊 Голосовые ответы: <b>ВКЛЮЧЕНЫ</b>",
        "voice_off": "🔇 Голосовые ответы: <b>ВЫКЛЮЧЕНЫ</b>",
        "btn_toggle_voice": "🔊/🔇 Вкл/Выкл голос",
        "btn_lang": "🌐 Сменить язык"
    }
}

def tr(key: str, lang: str = "uz", **kwargs) -> str:
    lang_msgs = MESSAGES.get(lang, MESSAGES["uz"])
    text = lang_msgs.get(key, MESSAGES["uz"].get(key, f"[{key}]"))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
