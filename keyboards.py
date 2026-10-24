# -*- coding: utf-8 -*-
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from locales import tr


def get_main_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Hotira77 uchun asosiy minimalist menyu."""
    btn_auto = tr("btn_auto_radar", lang)
    btn_rem = tr("btn_reminders", lang)
    btn_doc = tr("btn_documents", lang)
    btn_ai = tr("btn_ai", lang)
    btn_set = tr("btn_settings", lang)

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=btn_auto, request_location=True)],
            [KeyboardButton(text=btn_rem), KeyboardButton(text=btn_doc)],
            [KeyboardButton(text=btn_ai), KeyboardButton(text=btn_set)]
        ],
        resize_keyboard=True,
        input_field_placeholder="Xabar yozing yoki ovoz yuboring (Gemini AI javob beradi)..."
    )


def get_cancel_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Bekor qilish klaviaturasi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr("btn_cancel", lang))]
        ],
        resize_keyboard=True
    )


def get_ai_mode_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """AI Maslahatchi suhbat klaviaturasi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr("btn_clear_chat", lang))],
            [KeyboardButton(text=tr("btn_back_main", lang))]
        ],
        resize_keyboard=True
    )


def get_reminders_main_kb(reminders: list, lang: str = "uz") -> InlineKeyboardMarkup:
    """Eslatmalar ro'yxati va boshqarish klaviaturasi."""
    buttons = []
    for r in reminders[:15]:
        r_id = r["id"]
        time_part = r["remind_at"][11:16] if len(r["remind_at"]) >= 16 else r["remind_at"]
        text_short = r["text"] if len(r["text"]) <= 24 else r["text"][:21] + "..."
        buttons.append([
            InlineKeyboardButton(
                text=f"⏰ {time_part} | {text_short}",
                callback_data=f"rem_view:{r_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(text=tr("btn_add_rem", lang), callback_data="rem_new")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_reminder_item_kb(reminder_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """Bitta eslatma boshqaruv klaviaturasi."""
    buttons = [
        [
            InlineKeyboardButton(text=tr("btn_done", lang), callback_data=f"rem_done:{reminder_id}"),
            InlineKeyboardButton(text=tr("btn_delete", lang), callback_data=f"rem_del:{reminder_id}")
        ],
        [
            InlineKeyboardButton(text="◀️ " + tr("btn_back_main", lang), callback_data="rem_list")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_reminder_alert_kb(reminder_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """Eslatma vaqti kelganda chiquvchi ogohlantirish oynasi."""
    buttons = [
        [
            InlineKeyboardButton(text=tr("btn_done", lang), callback_data=f"rem_done:{reminder_id}"),
            InlineKeyboardButton(text=tr("btn_snooze", lang), callback_data=f"rem_snooze:{reminder_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_documents_inline_kb(docs: list, lang: str = "uz") -> InlineKeyboardMarkup:
    """Saqlangan xotiralar va hujjatlar ro'yxati."""
    buttons = []
    type_icons = {
        "photo": "🖼",
        "video": "🎥",
        "audio": "🎵",
        "voice": "🎙",
        "document": "📄",
        "note": "📝"
    }
    for d in docs[:25]:
        d_id = d["id"]
        itype = d.get("item_type", "document")
        icon = type_icons.get(itype, "📁")
        caption = (d.get("caption") or "").strip()
        fname = (d.get("file_name") or "").strip()
        display_name = caption if caption else (fname if fname else f"Fayl #{d_id}")
        if len(display_name) > 28:
            display_name = display_name[:25] + "..."
        buttons.append([
            InlineKeyboardButton(text=f"{icon} {display_name}", callback_data=f"doc_view:{d_id}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_document_single_kb(doc_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """Bitta hujjat yoki xotira amallari."""
    buttons = [
        [
            InlineKeyboardButton(text="📥 Ochish / Yuklash", callback_data=f"doc_get:{doc_id}"),
            InlineKeyboardButton(text="🗑 " + tr("btn_delete", lang), callback_data=f"doc_del_ask:{doc_id}")
        ],
        [
            InlineKeyboardButton(text="◀️ " + tr("btn_back_main", lang), callback_data="doc_list")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_doc_delete_confirm_kb(doc_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """Hujjatni o'chirishni tasdiqlash."""
    buttons = [
        [
            InlineKeyboardButton(text="🗑 Ha, o'chirilsin", callback_data=f"doc_del_confirm:{doc_id}"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data=f"doc_view:{doc_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_settings_keyboard(lang: str = "uz", voice_enabled: bool = True) -> InlineKeyboardMarkup:
    """Sozlamalar klaviaturasi."""
    v_text = "🔊 Ovoz: Yoqilgan" if voice_enabled else "🔇 Ovoz: O'chirilgan"
    if lang == "ru":
        v_text = "🔊 Голос: Включен" if voice_enabled else "🔇 Голос: Выключен"

    buttons = [
        [InlineKeyboardButton(text=v_text, callback_data="toggle_voice")],
        [InlineKeyboardButton(text=tr("btn_lang", lang), callback_data="show_lang_kb")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_language_inline_kb() -> InlineKeyboardMarkup:
    """Til tanlash oynasi."""
    buttons = [
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="set_lang:uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
