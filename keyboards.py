from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from locales import tr
from config import (
    ICON_DOCUMENTS,
    ICON_REMINDERS,
    ICON_AI
)

def apply_icon(label: str, icon: str = "") -> str:
    """Agar foydalanuvchi .env da stiker ko'rsatgan bo'lsa qo'shadi, aks holda toza matn."""
    clean_icon = (icon or "").strip()
    return f"{clean_icon} {label}".strip() if clean_icon else label


# ==========================================
# ASOSIY REPLY KLAVIATURALAR (XOTIRA BOT)
# ==========================================

def get_main_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Xotira va Eslatmalar boti uchun minimalist va qulay bosh menyu."""
    btn_auto = "📍 AVTO-RADAR (Qayerdaman)" if lang == "uz" else "📍 АВТО-РАДАР (Где я)"
    btn_rem = apply_icon("⏰ " + tr("btn_reminders", lang) if "⏰" not in tr("btn_reminders", lang) else tr("btn_reminders", lang), ICON_REMINDERS)
    btn_doc = apply_icon("📁 " + tr("btn_documents", lang) if "📁" not in tr("btn_documents", lang) else tr("btn_documents", lang), ICON_DOCUMENTS)
    btn_ai = apply_icon("🤖 " + tr("btn_ai", lang) if "🤖" not in tr("btn_ai", lang) else tr("btn_ai", lang), ICON_AI)

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=btn_auto, request_location=True)],
            [KeyboardButton(text=btn_rem), KeyboardButton(text=btn_doc)],
            [KeyboardButton(text=btn_ai)]
        ],
        resize_keyboard=True,
        input_field_placeholder="AI ga savol yozing yoki eslatma yuboring..."
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

# ==========================================
# HUJJATLAR (DOCUMENTS) INLINE KLAVIATURALARI
# ==========================================

def get_documents_inline_kb(docs: list, page: int = 1, total_count: int = 0,
                            per_page: int = 5, lang: str = "uz") -> InlineKeyboardMarkup:
    """Hujjatlar ro'yxati va sahifalash klaviaturasi."""
    buttons = []
    total_pages = max(1, (total_count + per_page - 1) // per_page)

    for doc in docs:
        file_name = doc.get("file_name", "Hujjat")
        short_name = file_name if len(file_name) <= 32 else file_name[:29] + "..."
        buttons.append([
            InlineKeyboardButton(text=short_name, callback_data=f"doc_view:{doc['id']}")
        ])

    # Sahifalash qatori
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text=tr("btn_prev", lang), callback_data=f"docs_page:{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text=tr("btn_next", lang), callback_data=f"docs_page:{page+1}"))

    if nav_row:
        buttons.append(nav_row)

    # Qidiruv qatori
    buttons.append([
        InlineKeyboardButton(text=tr("btn_search_doc", lang), callback_data="docs_search")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_document_single_kb(doc_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """Bitta hujjatni ko'rish va boshqarish klaviaturasi."""
    buttons = [
        [
            InlineKeyboardButton(text=tr("btn_open_doc", lang), callback_data=f"doc_get:{doc_id}"),
            InlineKeyboardButton(text=tr("btn_delete", lang), callback_data=f"doc_del_confirm:{doc_id}")
        ],
        [
            InlineKeyboardButton(text=tr("btn_back_main", lang), callback_data="docs_page:1")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_doc_delete_confirm_kb(doc_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """Hujjatni o'chirishni tasdiqlash oynasi."""
    buttons = [
        [
            InlineKeyboardButton(text=tr("btn_yes", lang), callback_data=f"doc_del_yes:{doc_id}"),
            InlineKeyboardButton(text=tr("btn_no", lang), callback_data=f"doc_view:{doc_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==========================================
# ESLATMALAR (REMINDERS) INLINE KLAVIATURALARI
# ==========================================

def get_reminders_main_kb(reminders: list, lang: str = "uz") -> InlineKeyboardMarkup:
    """Eslatmalar ro'yxati va boshqarish klaviaturasi."""
    buttons = []
    for r in reminders:
        r_id = r["id"]
        time_part = r["remind_at"][11:16] if len(r["remind_at"]) >= 16 else r["remind_at"]
        text_short = r["text"] if len(r["text"]) <= 26 else r["text"][:23] + "..."
        buttons.append([
            InlineKeyboardButton(
                text=f"{time_part} | {text_short}",
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
            InlineKeyboardButton(text=tr("btn_back_main", lang), callback_data="rem_list")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_reminder_alert_kb(reminder_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """Eslatma vaqti kelganda yuboriladigan ogohlantirish oynasi."""
    buttons = [
        [
            InlineKeyboardButton(text=tr("btn_done", lang), callback_data=f"rem_done:{reminder_id}"),
            InlineKeyboardButton(text=tr("btn_snooze", lang), callback_data=f"rem_snooze:{reminder_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==========================================
# SOZLAMALAR (SETTINGS) VA TIL
# ==========================================

def get_language_inline_kb() -> InlineKeyboardMarkup:
    """Til tanlash oynasi."""
    buttons = [
        [
            InlineKeyboardButton(text="O'zbekcha", callback_data="set_lang:uz"),
            InlineKeyboardButton(text="Русский", callback_data="set_lang:ru")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
