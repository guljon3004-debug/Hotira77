# Minimalistik lokalizatsiya (O'zbek va Rus tillari)
# Hech qanday keraksiz stikerlarsiz, toza va professional matnlar

MESSAGES = {
    "uz": {
        # Asosiy tugmalar (Reply)
        "btn_work_in": "Keldim",
        "btn_work_out": "Ketdim",
        "btn_documents": "Hujjatlar",
        "btn_reminders": "Eslatmalar",
        "btn_report": "Ish vaqti hisoboti",
        "btn_ai": "AI Yordamchi",
        "btn_cancel": "Bekor qilish",
        "btn_back_main": "Asosiy menyu",
        "btn_clear_chat": "Suhbatni tozalash",

        # Start va Tizim
        "start_title": "<b>Xush kelibsiz, {name}</b>",
        "start_desc": (
            "<b>SHAXSIY XOTIRA VA ESLATMALAR YORDAMCHISI</b>\n\n"
            "Tizim ish vaqtingizni (Wi-Fi orqali avtomatik), rasmiy hujjatlaringizni "
            "va muhim eslatmalaringizni boshqaradi.\n\n"
            "<i>Istalgan PDF, Word, Excel yoki arxiv fayllarni yuboring — ular xavfsiz saqlanadi.</i>"
        ),
        "unauthorized": "Kirish cheklangan. Ushbu bot faqat egasi uchun ishlaydi.",

        # Davomat (Ishga kelish va ketish)
        "work_in_success": (
            "<b>KELISH QAYD ETILDI</b>\n\n"
            "Vaqt: <code>{time}</code>\n"
            "Usul: {method}\n\n"
            "<i>Kuningiz unumli va muvaffaqiyatli o'tsin.</i>"
        ),
        "work_in_already": (
            "<b>FAOL ISH VAQTI DAVOM ETMOQDA</b>\n\n"
            "Bugun kelgan vaqtingiz: <code>{time}</code>\n"
            "<i>Hali ishdan ketish qayd etilmagan.</i>"
        ),
        "work_out_success": (
            "<b>ISH YAKUNLANDI</b>\n\n"
            "Kelgan vaqt: <code>{check_in}</code>\n"
            "Ketgan vaqt: <code>{check_out}</code>\n"
            "Ishlangan vaqt: <b>{hours} soat {minutes} daqiqa</b>\n\n"
            "<i>Yaxshi dam oling.</i>"
        ),
        "work_out_no_session": (
            "<b>FAOL ISH KUNI TOPILMADI</b>\n\n"
            "Avval kelish qayd etilmagan yoki allaqachon ketganingiz belgilangan."
        ),
        "work_status_working": (
            "<b>JORIY HOLAT: ISHDA</b>\n\n"
            "Kelgan vaqtingiz: <code>{check_in}</code>\n"
            "O'tgan vaqt: {elapsed}\n"
            "Usul: {method}"
        ),
        "work_status_idle": (
            "<b>JORIY HOLAT: ISHDAN TASHQARI VAQT</b>\n\n"
            "<i>Bugun hali kelish qayd etilmagan yoki ish yakunlangan.</i>"
        ),
        "report_title": "<b>ISH VAQTI VA DAVOMAT HISOBOTI</b>\n\n",
        "report_summary": (
            "Davr: {year}-yil, {month}-oy\n"
            "Ishlangan kunlar: <b>{days} kun</b>\n"
            "Jami ishlangan vaqt: <b>{hours} soat {minutes} daqiqa</b>\n"
            "O'rtacha kunlik: {avg_h} soat {avg_m} daqiqa\n\n"
            "<b>So'nggi qaydlar:</b>\n{logs}"
        ),
        "report_empty": "<i>Ushbu oyda hali ish vaqti qaydlari mavjud emas.</i>",

        # Wi-Fi Avtomatizatsiya Yo'riqnomasi
        "wifi_guide_title": "<b>WI-FI ORQALI AVTOMATIK KELISH/KETISH SOZLASH</b>\n\n",
        "wifi_guide_body": (
            "Ishxona Wi-Fi tarmog'iga ulanganda bot avtomatik <b>«Keldingiz»</b>, "
            "tarmoqdan uzilganda esa <b>«Ketdingiz»</b> deb yozishi uchun telefoningizda 2 daqiqada ulab qo'yishingiz mumkin:\n\n"
            "<b>Android uchun (MacroDroid yoki Tasker):</b>\n"
            "1. Google Play'dan bepul MacroDroid o'rnating.\n"
            "2. Trigger: Ulanishlar -> Wi-Fi holati -> Tarmoqqa ulandi (Ishxona Wi-Fi tanlanadi)\n"
            "3. Action: Ilovalar -> HTTP Request (GET) -> Havola:\n"
            "<code>https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text=/wifi_in</code>\n"
            "4. Wi-Fi uzilganda text=/wifi_out bilan 2-makros yaratiladi.\n\n"
            "<b>iPhone uchun (Buyruqlar / Shortcuts):</b>\n"
            "1. «Команды (Shortcuts)» ilovasida «Автоматизация» bo'limiga kiring.\n"
            "2. «Создать автоматизацию» -> «Wi-Fi» -> Ishxona Wi-Fi tanlanadi.\n"
            "3. Amal qo'shish: «Получить содержимое URL» (GET so'rovi) yuqoridagi havola bilan."
        ),

        # Hujjatlar bo'limi
        "docs_title": "<b>HUJJATLAR ARXIVI</b>\n\nJami hujjatlar: <b>{count} ta</b>\nKerakli hujjatni tanlang yoki nomini yozib qidiring:",
        "docs_empty": "<b>Hujjatlar arxivi bo'sh.</b>\n\nIstalgan PDF, Word, Excel, TXT yoki ZIP faylini yuboring — tizim avtomatik saqlaydi.",
        "doc_saved": (
            "<b>HUJJAT SAQLANDI</b>\n\n"
            "Nomi: <code>{name}</code>\n"
            "Hajmi: {size}\n"
            "Sana: {date}"
        ),
        "doc_search_prompt": "<b>Qidiruv:</b> Qidirmoqchi bo'lgan hujjat nomini yoki kalit so'zni yozing:",
        "doc_search_results": "<b>«{query}» bo'yicha topilgan hujjatlar:</b>",
        "doc_not_found": "Hujjat topilmadi.",
        "doc_deleted": "Hujjat arxivdan o'chirildi.",
        "doc_del_confirm": "Haqiqatan ham ushbu hujjatni o'chirmoqchimisiz?",
        "media_not_supported": (
            "Ushbu bot faqat rasmiy hujjatlar (PDF, Word, Excel, TXT, ZIP) bilan ishlaydi.\n\n"
            "Foto va videolarni shaxsiy guruhingizga saqlash tavsiya etiladi."
        ),

        # Eslatmalar bo'limi
        "reminders_title": "<b>ESLATMALAR VA REJALAR</b>\n\nFaol eslatmalar: <b>{count} ta</b>",
        "reminders_empty": "<b>Hozirda faol eslatmalar yo'q.</b>\n\nYangi eslatma yaratish uchun pastdagi tugmani bosing yoki yozing (masalan: <i>«Ertaga 10:00 da hisobot topshirish»</i>).",
        "rem_new_prompt": "<b>Yangi eslatma yaratish:</b>\n\nVaqt va vazifani yozing (masalan: <i>«16:30 da bankka qo'ng'iroq qilish»</i> yoki <i>«Ertaga 09:00 da majlis»</i>):",
        "rem_saved": "<b>ESLATMA SAQLANDI</b>\n\nVazifa: {text}\nVaqt: <code>{time}</code>",
        "rem_alert": "<b>ESLATMA VAQTI KELDI</b>\n\nVazifa: {text}\nBelgilangan vaqt: {time}",
        "rem_done": "Vazifa bajarildi deb belgilandi.",
        "rem_snoozed": "Eslatma 10 daqiqaga kechiktirildi.",
        "rem_deleted": "Eslatma o'chirildi.",

        # AI Chat
        "ai_welcome": (
            "<b>AI YORDAMCHI (GOOGLE GEMINI)</b>\n\n"
            "Ish bo'yicha istalgan savolingizni yozing yoki ovozli xabar yuboring. "
            "Rasmiy xat loyihalash, hisobot tuzish yoki matn tahrirlashda yordam beraman.\n\n"
            "<i>Chiqish uchun «Asosiy menyu» tugmasini bosing.</i>"
        ),
        "ai_cleared": "Suhbat tarixi tozalandi.",
        "ai_processing": "Javob tayyorlanmoqda...",

        # Umumiy tugmalar
        "btn_today_status": "Bugungi holat",
        "btn_wifi_setup": "Wi-Fi sozlash",
        "btn_add_rem": "Yangi eslatma",
        "btn_search_doc": "Qidirish",
        "btn_open_doc": "Yuklab olish",
        "btn_delete": "O'chirish",
        "btn_yes": "Ha, o'chirish",
        "btn_no": "Yo'q, qolsin",
        "btn_done": "Bajarildi",
        "btn_snooze": "10 daqiqa",
        "btn_prev": "Oldingi",
        "btn_next": "Keyingi",
    },

    "ru": {
        # Главные кнопки (Reply)
        "btn_work_in": "Прибыл",
        "btn_work_out": "Ушел",
        "btn_documents": "Документы",
        "btn_reminders": "Напоминания",
        "btn_report": "Отчет о времени",
        "btn_ai": "AI Ассистент",
        "btn_cancel": "Отмена",
        "btn_back_main": "Главное меню",
        "btn_clear_chat": "Очистить диалог",

        # Старт и Система
        "start_title": "<b>Добро пожаловать, {name}</b>",
        "start_desc": (
            "<b>ОФИСНЫЙ ПЕРСОНАЛЬНЫЙ АССИСТЕНТ</b>\n\n"
            "Система учитывает рабочее время (автоматически по Wi-Fi), управляет "
            "документами и напоминаниями.\n\n"
            "<i>Отправляйте PDF, Word, Excel или архивы — они будут сохранены.</i>"
        ),
        "unauthorized": "Доступ ограничен. Бот работает только для владельца.",

        # Посещаемость (Приход и Уход)
        "work_in_success": (
            "<b>ПРИХОД ЗАФИКСИРОВАН</b>\n\n"
            "Время: <code>{time}</code>\n"
            "Метод: {method}\n\n"
            "<i>Желаем продуктивного дня.</i>"
        ),
        "work_in_already": (
            "<b>РАБОЧЕЕ ВРЕМЯ УЖЕ ИДЕТ</b>\n\n"
            "Время сегодняшнего прихода: <code>{time}</code>\n"
            "<i>Уход еще не зафиксирован.</i>"
        ),
        "work_out_success": (
            "<b>РАБОЧИЙ ДЕНЬ ЗАВЕРШЕН</b>\n\n"
            "Приход: <code>{check_in}</code>\n"
            "Уход: <code>{check_out}</code>\n"
            "Отработано: <b>{hours} ч {minutes} мин</b>\n\n"
            "<i>Хорошего отдыха.</i>"
        ),
        "work_out_no_session": (
            "<b>АКТИВНЫЙ РАБОЧИЙ ДЕНЬ НЕ НАЙДЕН</b>\n\n"
            "Приход еще не отмечался или уже завершен."
        ),
        "work_status_working": (
            "<b>ТЕКУЩИЙ СТАТУС: НА РАБОТЕ</b>\n\n"
            "Время прихода: <code>{check_in}</code>\n"
            "Прошло: {elapsed}\n"
            "Метод: {method}"
        ),
        "work_status_idle": (
            "<b>ТЕКУЩИЙ СТАТУС: ВНЕ РАБОТЫ</b>\n\n"
            "<i>Приход еще не отмечен или день завершен.</i>"
        ),
        "report_title": "<b>ОТЧЕТ ПО РАБОЧЕМУ ВРЕМЕНИ</b>\n\n",
        "report_summary": (
            "Период: {month}/{year}\n"
            "Отработано дней: <b>{days} дн.</b>\n"
            "Всего времени: <b>{hours} ч {minutes} мин</b>\n"
            "В среднем за день: {avg_h} ч {avg_m} мин\n\n"
            "<b>Последние записи:</b>\n{logs}"
        ),
        "report_empty": "<i>В этом месяце записей рабочего времени еще нет.</i>",

        # Инструкция по Wi-Fi
        "wifi_guide_title": "<b>АВТОМАТИЗАЦИЯ ПРИХОДА И УХОДА ПО WI-FI</b>\n\n",
        "wifi_guide_body": (
            "Бот может автоматически фиксировать приход при подключении к рабочему Wi-Fi "
            "и уход при отключении:\n\n"
            "<b>Для Android (MacroDroid / Tasker):</b>\n"
            "1. Установите MacroDroid.\n"
            "2. Триггер: Связь -> Состояние Wi-Fi -> Подключен к сети (рабочий Wi-Fi)\n"
            "3. Действие: HTTP запрос (GET):\n"
            "<code>https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text=/wifi_in</code>\n"
            "4. Для ухода такой же макрос с text=/wifi_out.\n\n"
            "<b>Для iPhone (Команды / Shortcuts):</b>\n"
            "1. «Команды» -> «Автоматизация» -> «Wi-Fi».\n"
            "2. «Получить содержимое URL» (запрос GET) с ссылкой выше."
        ),

        # Документы
        "docs_title": "<b>АРХИВ ДОКУМЕНТОВ</b>\n\nВсего документов: <b>{count}</b>\nВыберите документ или воспользуйтесь поиском:",
        "docs_empty": "<b>Архив документов пуст.</b>\n\nОтправьте любой PDF, Word, Excel, TXT или ZIP файл — бот сохранит его.",
        "doc_saved": (
            "<b>ДОКУМЕНТ СОХРАНЕН</b>\n\n"
            "Название: <code>{name}</code>\n"
            "Размер: {size}\n"
            "Дата: {date}"
        ),
        "doc_search_prompt": "<b>Поиск:</b> Введите название или ключевое слово для поиска:",
        "doc_search_results": "<b>Результаты поиска по «{query}»:</b>",
        "doc_not_found": "Документ не найден.",
        "doc_deleted": "Документ удален из архива.",
        "doc_del_confirm": "Вы действительно хотите удалить этот документ?",
        "media_not_supported": (
            "Бот работает только с официальными документами (PDF, Word, Excel, TXT, ZIP).\n\n"
            "Фото и видео рекомендуется сохранять в вашей личной группе."
        ),

        # Напоминания
        "reminders_title": "<b>НАПОМИНАНИЯ И ПЛАНЫ</b>\n\nАктивных напоминаний: <b>{count}</b>",
        "reminders_empty": "<b>Нет активных напоминаний.</b>\n\nЧтобы создать, нажмите кнопку ниже или напишите (например: <i>«Завтра в 10:00 отчет»</i>).",
        "rem_new_prompt": "<b>Новое напоминание:</b>\n\nНапишите время и задачу (например: <i>«В 16:30 позвонить в банк»</i> или <i>«Завтра в 09:00 собрание»</i>):",
        "rem_saved": "<b>НАПОМИНАНИЕ СОХРАНЕНО</b>\n\nЗадача: {text}\nВремя: <code>{time}</code>",
        "rem_alert": "<b>НАПОМИНАНИЕ</b>\n\nЗадача: {text}\nВремя: {time}",
        "rem_done": "Отмечено как выполненное.",
        "rem_snoozed": "Отложено на 10 минут.",
        "rem_deleted": "Напоминание удалено.",

        # AI Chat
        "ai_welcome": (
            "<b>AI АССИСТЕНТ (GOOGLE GEMINI)</b>\n\n"
            "Задайте любой вопрос или отправьте голосовое сообщение. Помогу составить письмо, отчет или отредактировать текст.\n\n"
            "<i>Для выхода нажмите «Главное меню».</i>"
        ),
        "ai_cleared": "История диалога очищена.",
        "ai_processing": "Подготовка ответа...",

        # Общие кнопки
        "btn_today_status": "Статус сегодня",
        "btn_wifi_setup": "Настройка Wi-Fi",
        "btn_add_rem": "Новое напоминание",
        "btn_search_doc": "Поиск",
        "btn_open_doc": "Скачать",
        "btn_delete": "Удалить",
        "btn_yes": "Да, удалить",
        "btn_no": "Нет, оставить",
        "btn_done": "Выполнено",
        "btn_snooze": "10 минут",
        "btn_prev": "Назад",
        "btn_next": "Вперед",
    }
}


def tr(key: str, lang: str = "uz", **kwargs) -> str:
    """Tarjima matnini qaytaradi va formatlaydi."""
    clean_lang = "ru" if lang == "ru" else "uz"
    text = MESSAGES.get(clean_lang, {}).get(key, MESSAGES["uz"].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
