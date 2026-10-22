import os
import sys
import re
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
import aiohttp
from aiohttp import web

# Windows konsolida UTF-8 to'g'ri ko'rinishi uchun
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import (
    FSInputFile,
    BotCommand,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramBadRequest

from config import (
    BOT_TOKEN,
    ADMIN_ID,
    WIFI_PORT,
    GROUP_ID,
    DOCS_TOPIC_ID,
    validate_config
)
from locales import tr
from database import (
    init_db,
    record_check_in,
    record_check_out,
    get_today_attendance,
    get_monthly_attendance,
    add_document,
    get_documents,
    get_document,
    delete_document,
    add_reminder,
    get_due_reminders,
    mark_reminder_completed,
    snooze_reminder,
    get_user_reminders,
    delete_reminder,
    get_user_lang,
    set_user_lang,
    is_voice_enabled,
    set_voice_enabled,
    is_user_authorized,
    log_security_incident,
    get_security_incidents,
    get_security_incident_count,
    get_authorized_users
)
from reminder_helper import parse_reminder_time, format_datetime
from keyboards import (
    get_main_keyboard,
    get_cancel_keyboard,
    get_ai_mode_keyboard,
    get_attendance_inline_kb,
    get_documents_inline_kb,
    get_document_single_kb,
    get_doc_delete_confirm_kb,
    get_reminders_main_kb,
    get_reminder_item_kb,
    get_reminder_alert_kb,
    get_language_inline_kb
)
from ai_chat import gemini_service
from tts_service import generate_voice_message
from card_generator import (
    generate_attendance_card,
    generate_welcome_card,
    generate_checkin_card,
    generate_checkout_card,
    generate_location_card,
    generate_street_change_card
)
from location_service import (
    resolve_address,
    update_user_location,
    get_user_current_location,
    format_location_text,
    calculate_distance_meters
)

# Log sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Konfiguratsiyani tekshirish va bazani ishga tushirish
validate_config()
init_db()

# Bot va Dispatcher obyektlari
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Global aiohttp sessiyasi
http_session: aiohttp.ClientSession | None = None

# Foydalanuvchilar holati (FSM alternativi):
# user_id -> {"mode": "default"|"ai_chat", "state": None|"search_doc"|"new_rem", "data": {}}
user_contexts: dict[int, dict] = {}


def get_user_ctx(user_id: int) -> dict:
    """Foydalanuvchi holatini qaytaradi (AI rejimi doimiy avtomatik)."""
    if user_id not in user_contexts:
        user_contexts[user_id] = {
            "mode": "ai_chat",
            "state": None,
            "data": {}
        }
    return user_contexts[user_id]


def format_file_size(size_bytes: int) -> str:
    """Fayl hajmini odam tushunadigan formatga o'tkazadi."""
    if not size_bytes:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


# ==========================================
# XAVFSIZLIK VA AVTORIZATSIYA (SECURITY FILTER)
# ==========================================

EMERGENCY_LOCKDOWN = False


class SecurityMiddleware(BaseMiddleware):
    """
    Qat'iy xavfsizlik nazoratchisi (Firewall):
    Begona foydalanuvchilarning barcha so'rovlarini avtomatik bloklaydi
    va bu haqda darhol Rahbar (Admin) ga xavfsizlik signali yuboradi.
    """
    async def __call__(self, handler, event: types.TelegramObject, data: dict):
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        user_id = user.id
        global EMERGENCY_LOCKDOWN

        # Favqulodda qulflangan holat
        if EMERGENCY_LOCKDOWN and str(user_id) != str(ADMIN_ID):
            if isinstance(event, types.Message):
                await event.answer(
                    "🔒 <b>TIZIM FAVQULODDA QULFLANGAN</b>\n\n"
                    "Xavfsizlik maqsadida barcha amallar rahbariyat tomonidan vaqtincha to'xtatilgan.",
                    parse_mode="HTML"
                )
            elif isinstance(event, types.CallbackQuery):
                await event.answer("Tizim favqulodda qulflangan!", show_alert=True)
            return

        # Ruxsatni tekshiramiz
        if not is_user_authorized(user_id, admin_id=ADMIN_ID):
            full_name = user.full_name or "Noma'lum"
            username = user.username or ""
            text_content = ""
            if isinstance(event, types.Message):
                text_content = event.text or event.caption or "[Hujjat/Media]"
            elif isinstance(event, types.CallbackQuery):
                text_content = f"[Tugma: {event.data}]"

            # Xavfsizlik hodisasini bazaga qayd etamiz
            log_security_incident(user_id, full_name, username, text_content)

            # Begonaga qat'iy va rasmiy rad javobi
            denied_msg = (
                "⛔ <b>KIRISH CHEKLANGAN</b>\n\n"
                "Ushbu bot faqat ofis rahbariyati va ruxsat berilgan xodimlar uchun maxfiy tizimdir. "
                "Sizda tizimdan foydalanish huquqi yo'q.\n\n"
                f"<i>Sizning ID raqamingiz: <code>{user_id}</code></i>"
            )
            if isinstance(event, types.Message):
                await event.answer(denied_msg, parse_mode="HTML")
            elif isinstance(event, types.CallbackQuery):
                await event.answer("Kirish cheklangan! Ushbu bot faqat egasi uchun ishlaydi.", show_alert=True)

            # RAHBARGA DARHOL XAVFSIZLIK SIGNALINI YUBORISH
            if ADMIN_ID and ADMIN_ID.isdigit() and int(ADMIN_ID) != user_id:
                try:
                    alert_text = (
                        "🚨 <b>XAVFSIZLIK BILDIRISHNOMASI</b>\n\n"
                        "Begona foydalanuvchi botga ulanishga urindi va <b>avtomatik bloklandi</b>:\n\n"
                        f"• <b>Ism:</b> {full_name}\n"
                        f"• <b>Username:</b> @{username if username else 'mavjud emas'}\n"
                        f"• <b>Telegram ID:</b> <code>{user_id}</code>\n"
                        f"• <b>So'rov:</b> <code>{text_content[:100]}</code>\n"
                        f"• <b>Vaqt:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        "<i>Holat: Kirish darhol to'xtatildi.</i>"
                    )
                    await bot.send_message(chat_id=int(ADMIN_ID), text=alert_text, parse_mode="HTML")
                except Exception as e:
                    logger.warning("Admin xavfsizlik signalida xatolik: %s", e)

            return  # To'xtatiladi, bot boshqa javob qaytarmaydi!

        return await handler(event, data)


# Xavfsizlik nazoratchisini barcha xabarlar va tugmalarga biriktiramiz
dp.message.outer_middleware(SecurityMiddleware())
dp.callback_query.outer_middleware(SecurityMiddleware())



# ==========================================
# DAVOMAT AMALLARI (ATTENDANCE)
# ==========================================

async def process_check_in(user_id: int, method: str = "Wi-Fi avtomat") -> str:
    """Kelishni qayd etish mantiqi."""
    lang = get_user_lang(user_id)
    res = record_check_in(user_id, method=method)

    if res["status"] == "already_active":
        return tr("work_in_already", lang, time=res["check_in_time"][:5])

    return tr("work_in_success", lang, time=res["check_in_time"][:5], method=method)


async def process_check_out(user_id: int, method: str = "Wi-Fi avtomat") -> str:
    """Ketishni qayd etish mantiqi."""
    lang = get_user_lang(user_id)
    res = record_check_out(user_id, method=method)

    if res["status"] == "no_active_session":
        return tr("work_out_no_session", lang)

    return tr(
        "work_out_success", lang,
        check_in=res["check_in_time"][:5],
        check_out=res["check_out_time"][:5],
        hours=res["hours"],
        minutes=res["minutes"]
    )


def generate_attendance_report_text(user_id: int) -> str:
    """Oylik davomat hisoboti matnini shakllantiradi."""
    lang = get_user_lang(user_id)
    now = datetime.now()
    rows, summary = get_monthly_attendance(user_id, now.year, now.month)

    if not rows:
        return tr("report_title", lang) + tr("report_empty", lang)

    log_lines = []
    # Oxirgi 7 ta yozuvni ko'rsatish
    for r in rows[:7]:
        d = r["work_date"][5:]  # MM-DD
        cin = r["check_in_time"][:5] if r.get("check_in_time") else "--:--"
        cout = r["check_out_time"][:5] if r.get("check_out_time") else "ishda"
        dur = f"{r.get('duration_minutes', 0) // 60}s {r.get('duration_minutes', 0) % 60}d" if r.get("status") == "completed" else "faol"
        log_lines.append(f"• <b>{d}:</b> {cin} - {cout} ({dur})")

    logs_text = "\n".join(log_lines)
    body = tr(
        "report_summary", lang,
        year=summary["year"],
        month=summary["month"],
        days=summary["total_days"],
        hours=summary["total_hours"],
        minutes=summary["remaining_mins"],
        avg_h=summary["avg_hours"],
        avg_m=summary["avg_mins"],
        logs=logs_text
    )
    return tr("report_title", lang) + body


# ==========================================
# BUYRUQLAR (COMMANDS) VA ASOSIY MENU
# ==========================================

@dp.message(CommandStart())
async def handle_start(message: types.Message):
    """Start buyrug'i (Bej va jigarrang muqova kartochkasi bilan)."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    ctx = get_user_ctx(user_id)
    ctx["mode"] = "default"
    ctx["state"] = None

    name = message.from_user.full_name
    title = tr("start_title", lang, name=name)
    desc = tr("start_desc", lang)

    card_path = f"downloads/welcome_{user_id}.png"
    try:
        generate_welcome_card(name=name, output_path=card_path)
        if os.path.exists(card_path):
            await message.answer_photo(
                photo=FSInputFile(card_path),
                caption=f"{title}\n\n{desc}",
                parse_mode="HTML",
                reply_markup=get_main_keyboard(lang)
            )
            return
    except Exception as e:
        logger.warning("Muqova kartochkasida xatolik: %s", e)

    await message.answer(
        f"{title}\n\n{desc}",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(lang)
    )


@dp.message(Command("wifi_in", "keldim", "in"))
async def cmd_wifi_in(message: types.Message):
    """Wi-Fi yoki qo'lda kelish buyrug'i."""
    user_id = message.from_user.id
    text = await process_check_in(user_id, method="Wi-Fi / Buyruq")
    lang = get_user_lang(user_id)
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(lang))


@dp.message(Command("wifi_out", "ketdim", "out"))
async def cmd_wifi_out(message: types.Message):
    """Wi-Fi yoki qo'lda ketish buyrug'i."""
    user_id = message.from_user.id
    text = await process_check_out(user_id, method="Wi-Fi / Buyruq")
    lang = get_user_lang(user_id)
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(lang))


@dp.message(Command("report", "tabel"))
async def cmd_report(message: types.Message):
    """Oylik davomat hisoboti buyrug'i (Bej va jigarrang kartochka bilan)."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    text = generate_attendance_report_text(user_id)

    att = get_today_attendance(user_id)
    cin = att["check_in_time"][:5] if att and att.get("check_in_time") else "--:--"
    cout = att["check_out_time"][:5] if att and att.get("check_out_time") else "--:--"
    dur_mins = att.get("duration_minutes", 0) if att else 0
    dur_str = f"{dur_mins // 60}s {dur_mins % 60}d" if dur_mins > 0 else ("Ishda" if att and att.get("status") == "working" else "--:--")
    status_str = "Ishda" if att and att.get("status") == "working" else "Yakunlangan"

    card_path = f"downloads/card_{user_id}.png"
    try:
        generate_attendance_card(
            title="Ish vaqti hisoboti",
            check_in=cin,
            check_out=cout,
            duration=dur_str,
            status_text=status_str,
            output_path=card_path
        )
        if os.path.exists(card_path):
            await message.answer_photo(
                photo=FSInputFile(card_path),
                caption=text,
                parse_mode="HTML",
                reply_markup=get_attendance_inline_kb(lang)
            )
            return
    except Exception as e:
        logger.warning("Kartochka yaratishda xatolik: %s", e)

    await message.answer(text, parse_mode="HTML", reply_markup=get_attendance_inline_kb(lang))


@dp.message(Command("ai"))
async def cmd_ai_quick(message: types.Message, command: CommandObject):
    """Tezkor Gemini AI savol-javobi: /ai <savol>."""
    user_id = message.from_user.id
    prompt = (command.args or "").strip()

    if not prompt:
        await message.answer(
            "Savolingizni buyruqdan keyin yozing:\nMasalan: <code>/ai Rasmiy xat qanday yoziladi?</code>",
            parse_mode="HTML"
        )
        return

    global http_session
    if not http_session or http_session.closed:
        http_session = aiohttp.ClientSession()

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    response = await gemini_service.ask(user_id, prompt, http_session)
    await message.answer(response, parse_mode="HTML")


# ==========================================
# ASOSIY REPLY TUGMALARNI QABUL QILISH (MOSLASHUVCHAN)
# ==========================================

@dp.message(F.text.func(lambda t: bool(t and any(t.strip().endswith(k) for k in ["Keldim", "Прибыл"]))))
async def btn_handle_work_in(message: types.Message):
    """«Keldim» tugmasi (Bej va jigarrang kartochka bilan)."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    res = record_check_in(user_id, method="Qo'lda")

    if res["status"] == "already_active":
        text = tr("work_in_already", lang, time=res["check_in_time"][:5])
        await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(lang))
        return

    text = tr("work_in_success", lang, time=res["check_in_time"][:5], method="Qo'lda")
    card_path = f"downloads/in_{user_id}.png"
    try:
        generate_checkin_card(time_str=res["check_in_time"][:5], method_str="Qo'lda", output_path=card_path)
        if os.path.exists(card_path):
            await message.answer_photo(
                photo=FSInputFile(card_path),
                caption=text,
                parse_mode="HTML",
                reply_markup=get_main_keyboard(lang)
            )
            return
    except Exception as e:
        logger.warning("Kelish kartochkasida xatolik: %s", e)

    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(lang))


@dp.message(F.text.func(lambda t: bool(t and any(t.strip().endswith(k) for k in ["Ketdim", "Ушел"]))))
async def btn_handle_work_out(message: types.Message):
    """«Ketdim» tugmasi (Bej va jigarrang kartochka bilan)."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    res = record_check_out(user_id, method="Qo'lda")

    if res["status"] == "no_active_session":
        text = tr("work_out_no_session", lang)
        await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(lang))
        return

    dur_str = f"{res['hours']}s {res['minutes']}d"
    text = tr(
        "work_out_success", lang,
        check_in=res["check_in_time"][:5],
        check_out=res["check_out_time"][:5],
        hours=res["hours"],
        minutes=res["minutes"]
    )
    card_path = f"downloads/out_{user_id}.png"
    try:
        generate_checkout_card(
            check_in=res["check_in_time"][:5],
            check_out=res["check_out_time"][:5],
            duration=dur_str,
            output_path=card_path
        )
        if os.path.exists(card_path):
            await message.answer_photo(
                photo=FSInputFile(card_path),
                caption=text,
                parse_mode="HTML",
                reply_markup=get_main_keyboard(lang)
            )
            return
    except Exception as e:
        logger.warning("Ketish kartochkasida xatolik: %s", e)

    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(lang))



@dp.message(F.text.func(lambda t: bool(t and any(t.strip().endswith(k) for k in ["Ish vaqti hisoboti", "Отчет о времени", "Hisobot"]))))
async def btn_handle_report(message: types.Message):
    """«Ish vaqti hisoboti» tugmasi."""
    await cmd_report(message)


@dp.message(F.text.func(lambda t: bool(t and any(t.strip().endswith(k) for k in ["Hujjatlar", "Документы"]))))
async def btn_handle_documents(message: types.Message):
    """«Hujjatlar» bo'limi."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    ctx = get_user_ctx(user_id)
    ctx["state"] = None

    docs, total_count = get_documents(user_id, page=1, per_page=5)
    if total_count == 0:
        await message.answer(tr("docs_empty", lang), parse_mode="HTML", reply_markup=get_main_keyboard(lang))
        return

    text = tr("docs_title", lang, count=total_count)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_documents_inline_kb(docs, page=1, total_count=total_count, lang=lang)
    )


@dp.message(F.text.func(lambda t: bool(t and any(t.strip().endswith(k) for k in ["Eslatmalar", "Напоминания"]))))
async def btn_handle_reminders(message: types.Message):
    """«Eslatmalar» bo'limi."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    ctx = get_user_ctx(user_id)
    ctx["state"] = None

    rems = get_user_reminders(user_id, show_completed=False, limit=10)
    if not rems:
        await message.answer(
            tr("reminders_empty", lang),
            parse_mode="HTML",
            reply_markup=get_reminders_main_kb([], lang=lang)
        )
        return

    text = tr("reminders_title", lang, count=len(rems))
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_reminders_main_kb(rems, lang=lang)
    )


@dp.message(F.text.func(lambda t: bool(t and any(t.strip().endswith(k) for k in ["AI Yordamchi", "AI Maslahatchi", "AI Ассистент", "Gemini AI"]))))
async def btn_handle_ai(message: types.Message):
    """AI Maslahatchi ma'lumoti va tozalash menyusi."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    ctx = get_user_ctx(user_id)
    ctx["mode"] = "ai_chat"
    ctx["state"] = None

    await message.answer(
        "🤖 <b>AI Maslahatchi (Gemini AI) doimiy ravishda faol!</b>\n\n"
        "Siz istalgan paytda to'g'ridan-to'g'ri matn yoki ovozli xabar yuborishingiz mumkin — bot avtomatik javob beradi.\n\n"
        "🗑 <i>Suhbat xotirasini yangilash uchun quyidagi tugmani bosing:</i>",
        parse_mode="HTML",
        reply_markup=get_ai_mode_keyboard(lang)
    )


@dp.message(F.text.func(lambda t: bool(t and any(t.strip().endswith(k) for k in ["Suhbatni tozalash", "Очистить диалог"]))))
async def btn_handle_clear_chat(message: types.Message):
    """AI suhbatini tozalash."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    gemini_service.clear_history(user_id)
    await message.answer(tr("ai_cleared", lang), reply_markup=get_ai_mode_keyboard(lang))


@dp.message(F.text.func(lambda t: bool(t and any(t.strip().endswith(k) for k in ["Asosiy menyu", "Главное меню", "Bekor qilish", "Отмена"]))))
async def btn_handle_back_main(message: types.Message):
    """Asosiy menyuga qaytish."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    ctx = get_user_ctx(user_id)
    ctx["mode"] = "ai_chat"
    ctx["state"] = None

    await message.answer(
        "Asosiy menyudasiz. AI rejimi avtomatik faol:",
        reply_markup=get_main_keyboard(lang)
    )


# ==========================================
# GPS VA JONLI JOYLASHUV (LIVE LOCATION)
# ==========================================

@dp.message(F.location)
async def handle_user_location(message: types.Message):
    """
    Foydalanuvchi bittalik yoki Jonli joylashuv (Live Location) yuborganida.
    Avtomobil rejimida hech qanday buyruqsiz darhol ovoz bilan e'lon qiladi.
    """
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    loc = message.location
    lat, lon = loc.latitude, loc.longitude
    is_live = bool(loc.live_period)

    global http_session
    if not http_session or http_session.closed:
        http_session = aiohttp.ClientSession()

    await bot.send_chat_action(message.chat.id, ChatAction.FIND_LOCATION)
    addr = await resolve_address(lat, lon, http_session)
    road = addr.get("road") or "Ko'cha aniqlanmoqda"
    district = addr.get("district") or addr.get("city") or "Toshkent"
    now = datetime.now()

    addr["last_notified_road"] = road
    addr["last_notification_time"] = now
    update_user_location(user_id, lat, lon, addr, is_live=is_live)

    # 1. BIRINCHI O'RINDA OVOZLI XABAR (Haydovchi ekranga qaramasligi uchun!)
    if is_live:
        v_phrase = f"Avto-rejim ulandi. Hozir siz {road}dasiz. Ko'changiz o'zgarganda avtomatik aytib turaman. Oq yo'l!"
    else:
        v_phrase = f"Avto-rejim faollashdi. Siz hozir {road}dasiz, {district} hududida. Oq yo'l!"

    try:
        v_path = await generate_voice_message(v_phrase)
        if v_path and os.path.exists(v_path):
            cap = f"🚗 <b>Hozirgi ko'cha:</b> {road} ({district})"
            if is_live:
                cap += "\n<i>Jonli kuzatuv yoqildi. Ko'cha o'zgarganda ovoz bilan avtomat aytib turaman.</i>"
            else:
                cap += "\n💡 <i>Doimiy avtomatik eshitish uchun: 📎 Skrepka -> Joylashuv -> Jonli joylashuvni ulashish (8 soat).</i>"

            await bot.send_voice(
                chat_id=message.chat.id,
                voice=FSInputFile(v_path),
                caption=cap,
                parse_mode="HTML",
                reply_markup=get_main_keyboard(lang)
            )
            try:
                os.remove(v_path)
            except Exception:
                pass
    except Exception as e:
        logger.warning("Joylashuv ovozli xabarida xatolik: %s", e)
        await message.answer(f"🚗 Siz hozir <b>{road}</b>dasiz ({district}).", parse_mode="HTML", reply_markup=get_main_keyboard(lang))


@dp.edited_message(F.location)
async def handle_live_location_update(message: types.Message):
    """
    Foydalanuvchi avtomobilda harakatlanganda Telegram avtomatik yuboradigan GPS yangilanishlari.
    Ko'cha o'zgarganda hech qanday tugma yoki buyruqsiz to'liq avtomatik OVOZLI aytib turadi!
    """
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    loc = message.location
    lat, lon = loc.latitude, loc.longitude

    prev = get_user_current_location(user_id)
    # Kamida 20 metr siljish bo'lsa tekshiramiz (svetoforda turganda spam bo'lmasligi uchun)
    if prev:
        dist = calculate_distance_meters(prev["lat"], prev["lon"], lat, lon)
        if dist < 20:
            return

    global http_session
    if not http_session or http_session.closed:
        http_session = aiohttp.ClientSession()

    addr = await resolve_address(lat, lon, http_session)
    new_road = (addr.get("road") or "").strip()
    old_road = (prev.get("last_notified_road") or prev.get("road") or "").strip() if prev else ""
    now = datetime.now()
    last_time = (prev.get("last_notification_time") if prev else None) or datetime.min

    # 1. KO'CHA O'ZGARISHI — Tezkor lo'nda ovozli ogohlantirish!
    if new_road and old_road and new_road.lower() != old_road.lower():
        # Kamida 8 soniya oraliq
        if (now - last_time).total_seconds() >= 8:
            district = addr.get("district") or addr.get("city") or "Toshkent"
            voice_phrase = f"Siz {new_road} ko'chasiga o'tdingiz."

            try:
                voice_path = await generate_voice_message(voice_phrase)
                if voice_path and os.path.exists(voice_path):
                    await bot.send_voice(
                        chat_id=message.chat.id,
                        voice=FSInputFile(voice_path),
                        caption=f"🚗 <b>Yangi ko'cha:</b> {new_road} ({district})\n📍 <i>Oldingi ko'cha: {old_road}</i>",
                        parse_mode="HTML"
                    )
                    try:
                        os.remove(voice_path)
                    except Exception:
                        pass
            except Exception as e:
                logger.warning("Ko'cha o'zgarishi ovozida xatolik: %s", e)

            addr["last_notified_road"] = new_road
            addr["last_notification_time"] = now

    # 2. Yangi harakat boshlanganda birinchi e'lon
    elif not old_road and new_road:
        district = addr.get("district") or addr.get("city") or "Toshkent"
        voice_phrase = f"Harakat boshlandi. Siz {new_road}dasiz."
        try:
            voice_path = await generate_voice_message(voice_phrase)
            if voice_path and os.path.exists(voice_path):
                await bot.send_voice(
                    chat_id=message.chat.id,
                    voice=FSInputFile(voice_path),
                    caption=f"🚗 <b>Harakat kuzatilmoqda:</b> {new_road}",
                    parse_mode="HTML"
                )
                try:
                    os.remove(voice_path)
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Boshlang'ich ovoz xatosi: %s", e)

        addr["last_notified_road"] = new_road
        addr["last_notification_time"] = now

    # 3. Katta trassada (bitta ko'chada uzoq yurganda — har 5 daqiqada faollik xabari)
    elif new_road and (now - last_time).total_seconds() >= 300:
        voice_phrase = f"Harakat davom etmoqda. Siz haligacha {new_road}dasiz."
        try:
            voice_path = await generate_voice_message(voice_phrase)
            if voice_path and os.path.exists(voice_path):
                await bot.send_voice(
                    chat_id=message.chat.id,
                    voice=FSInputFile(voice_path),
                    caption=f"🚗 <i>Harakat davom etmoqda:</i> {new_road}",
                    parse_mode="HTML"
                )
                try:
                    os.remove(voice_path)
                except Exception:
                    pass
        except Exception:
            pass
        addr["last_notification_time"] = now

    update_user_location(user_id, lat, lon, addr, is_live=True)


@dp.message(F.text.func(lambda t: bool(t and any(k in t.lower() for k in ["qayerdaman", "qayerda turibman", "qaysi kochadaman", "qaysi ko'chadaman", "где я", "какой улице"]))))
async def handle_where_am_i(message: types.Message):
    """«Qayerdaman?» savoliga javob berish (Ovoz va kartochka bilan)."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    loc_data = get_user_current_location(user_id)

    if not loc_data:
        msg = (
            "<b>JONLI JOYLASHUV FAOL EMAS</b>\n\n"
            "Ko'chalarda yurganingizda qayerda ekanligingizni aniq bilish uchun:\n"
            "1. Pastdagi qog'oz qisqich (скрепка) 📎 belgisini bosing.\n"
            "2. «Геопозиция (Location)» bo'limini tanlang.\n"
            "3. «Транслировать мою геопозицию» (Jonli geolokatsiya) ni 8 soatga yoqing.\n\n"
            "<i>Shundan so'ng bot ko'chalardagi har bir qadamingizni avtomatik o'qib boradi.</i>"
        )
        await message.answer(msg, parse_mode="HTML", reply_markup=get_main_keyboard(lang))
        return

    road = loc_data.get("road") or "Ko'cha aniqlanmoqda"
    district = loc_data.get("district") or loc_data.get("city") or "Toshkent"
    time_str = loc_data.get("updated_at", datetime.now()).strftime("%H:%M:%S")

    card_path = f"downloads/loc_{user_id}.png"
    text = format_location_text(loc_data, lang=lang)
    sent_photo = False
    try:
        generate_location_card(road=road, district=district, time_str=time_str, output_path=card_path)
        if os.path.exists(card_path):
            await message.answer_photo(
                photo=FSInputFile(card_path),
                caption=text,
                parse_mode="HTML",
                reply_markup=get_main_keyboard(lang)
            )
            sent_photo = True
    except Exception as e:
        logger.warning("Joylashuv kartochkasida xatolik: %s", e)

    if not sent_photo:
        await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(lang))

    # Ovozli javob yuborish
    if is_voice_enabled(user_id):
        try:
            voice_ans = f"Siz hozir {road}dasiz. Hudud: {district}."
            voice_path = await generate_voice_message(voice_ans)
            if voice_path and os.path.exists(voice_path):
                await message.answer_voice(voice=FSInputFile(voice_path))
                try:
                    os.remove(voice_path)
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Ovozli javobda xatolik: %s", e)


@dp.message(Command("voice", "ovoz"))
@dp.message(F.text.func(lambda t: bool(t and any(k in t.lower() for k in [
    "ovozli ogohlantirish", "ovozli xabar", "ovozni yoq", "ovozli bildirishnoma",
    "овозли огохлантириш", "овозни ёқ", "овозли", "ovozli", "огохлантириш ёкиб", "огохлантиришни ёк"
]))))
async def handle_voice_toggle(message: types.Message):
    """Ovozli ogohlantirishni yoqish yoki holatini tekshirish."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    text = (message.text or "").lower()

    if any(k in text for k in ["o'chir", "ochir", "off", "отключ", "o'chirish", "ўчир"]):
        set_voice_enabled(user_id, False)
        msg = (
            "<b>OVOZLI OGOHLANTIRISH: O'CHIRILDI</b>\n\n"
            "Ko'chalar o'zgarganda faqat matnli va grafik kartochkalar yuboriladi.\n\n"
            "<i>Qayta yoqish uchun: /voice buyrug'ini yuboring yoki «Ovozni yoq» deb yozing.</i>"
        )
        await message.answer(msg, parse_mode="HTML", reply_markup=get_main_keyboard(lang))
        return

    set_voice_enabled(user_id, True)
    msg = (
        "<b>OVOZLI OGOHLANTIRISH: FAOL</b>\n\n"
        "Jonli geolokatsiya (Live Location) orqali ko'chalarda ketayotganingizda, "
        "bir ko'chadan ikkinchisiga o'tishingiz bilanoq bot avtomatik ovozli bildirishnoma jo'natadi.\n\n"
        "<b>Namuna:</b> <i>«Siz [Avvalgi ko'cha]dan [Yangi ko'cha]ga o'tdingiz»</i>\n\n"
        "<i>Ovoz namunasi quyida yuborildi.</i>"
    )
    await message.answer(msg, parse_mode="HTML", reply_markup=get_main_keyboard(lang))

    try:
        sample_path = await generate_voice_message(
            "Ovozli ogohlantirish muvaffaqiyatli yoqildi. Ko'changiz o'zgarganda sizga avtomatik ovozli xabar yuborib boraman."
        )
        if sample_path and os.path.exists(sample_path):
            await bot.send_voice(
                chat_id=message.chat.id,
                voice=FSInputFile(sample_path),
                caption="Ovozli bildirishnoma namunasi"
            )
            try:
                os.remove(sample_path)
            except Exception:
                pass
    except Exception as e:
        logger.warning("Ovoz namunasi yuborishda xatolik: %s", e)





# ==========================================
# RAHBAR UCHUN XAVFSIZLIK VA BOSHQARUV BUYRUQLARI
# ==========================================

@dp.message(Command("security", "xavfsizlik"))
async def cmd_security_status(message: types.Message):
    """Xavfsizlik tizimi holatini ko'rish (Faqat Rahbar uchun)."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    if str(user_id) != str(ADMIN_ID):
        return

    incidents_count = get_security_incident_count()
    auth_users = get_authorized_users()
    status_lock = "🔴 FAVQULODDA QULFLANGAN" if EMERGENCY_LOCKDOWN else "🟢 NORMAL (XAVFSIZ VA OCHIQ)"

    text = (
        "🛡 <b>XAVFSIZLIK VA HIMOYALASH TIZIMI</b>\n\n"
        f"• <b>Tizim Rahbari (Admin):</b> <code>{ADMIN_ID}</code>\n"
        f"• <b>Kirish filtri (Firewall):</b> 🟢 100% Faol\n"
        f"• <b>Begonalarni bloklash:</b> Avtomatik + Signal\n"
        f"• <b>Tizim holati:</b> {status_lock}\n"
        f"• <b>Qaytarilgan begona urinishlar:</b> {incidents_count} ta\n"
        f"• <b>Ruxsat berilgan xodimlar:</b> {len(auth_users)} ta\n\n"
        "<b>Boshqaruv buyruqlari:</b>\n"
        "• <code>/lock</code> — Tizimni favqulodda to'liq qulflash\n"
        "• <code>/unlock</code> — Tizimni qulfdan chiqarish"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(lang))


@dp.message(Command("lock", "qulfla"))
async def cmd_emergency_lock(message: types.Message):
    """Tizimni favqulodda qulflash (Faqat Rahbar uchun)."""
    user_id = message.from_user.id
    if str(user_id) != str(ADMIN_ID):
        return

    global EMERGENCY_LOCKDOWN
    EMERGENCY_LOCKDOWN = True
    await message.answer(
        "🔒 <b>TIZIM FAVQULODDA QULFLANDI</b>\n\n"
        "Barcha tashqi amallar va xizmatlar vaqtincha to'xtatildi.\n"
        "Tizimni qayta ochish uchun: <code>/unlock</code> buyrug'ini yuboring.",
        parse_mode="HTML"
    )


@dp.message(Command("unlock", "och"))
async def cmd_emergency_unlock(message: types.Message):
    """Tizimni qulfdan chiqarish (Faqat Rahbar uchun)."""
    user_id = message.from_user.id
    if str(user_id) != str(ADMIN_ID):
        return

    global EMERGENCY_LOCKDOWN
    EMERGENCY_LOCKDOWN = False
    await message.answer(
        "🔓 <b>TIZIM QULFDAN CHIQARILDI</b>\n\n"
        "Barcha xizmatlar, davomat va monitoring odatdagidek normal rejimda ishlamoqda.",
        parse_mode="HTML"
    )


# ==========================================
# HUJJATLAR (DOCUMENTS) YUKLASH VA ISHLASH
# ==========================================

@dp.message(F.document)
async def handle_document_upload(message: types.Message):
    """
    Foydalanuvchi hujjat (PDF, Word, Excel, ZIP va h.k.) yuborganida.
    """
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    doc = message.document

    file_name = doc.file_name or "Hujjat"
    file_size = doc.file_size or 0
    file_id = doc.file_id
    file_unique_id = doc.file_unique_id
    caption = message.caption or ""

    # Kengaytmani aniqlash (.pdf, .docx va h.k.)
    _, ext = os.path.splitext(file_name)
    ext = ext.lower().replace(".", "")

    # Bazaga saqlaymiz
    doc_id = add_document(
        user_id=user_id,
        file_id=file_id,
        file_unique_id=file_unique_id,
        file_name=file_name,
        file_size=file_size,
        file_ext=ext,
        caption=caption
    )

    # Agar shaxsiy guruh sozlangan bo'lsa, nusxasini guruhga ham jo'natamiz
    if GROUP_ID:
        try:
            thread_id = int(DOCS_TOPIC_ID) if DOCS_TOPIC_ID and DOCS_TOPIC_ID.isdigit() else None
            await message.copy_to(
                chat_id=int(GROUP_ID) if GROUP_ID.startswith("-") or GROUP_ID.isdigit() else GROUP_ID,
                message_thread_id=thread_id
            )
            logger.info("Hujjat guruhga uzatildi: %s -> %s", file_name, GROUP_ID)
        except Exception as e:
            logger.warning("Hujjatni guruhga uzatishda xatolik: %s", e)

    size_str = format_file_size(file_size)
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    text = tr("doc_saved", lang, name=file_name, size=size_str, date=date_str)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_document_single_kb(doc_id, lang=lang)
    )


@dp.message(F.photo)
async def handle_photo_message(message: types.Message):
    """Foydalanuvchi yuborgan rasmni Gemini AI orqali tahlil qilish."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    photo = message.photo[-1]
    photo_file = await bot.get_file(photo.file_id)
    import io
    photo_buffer = io.BytesIO()
    await bot.download_file(photo_file.file_path, destination=photo_buffer)
    photo_bytes = photo_buffer.getvalue()

    global http_session
    if not http_session or http_session.closed:
        http_session = aiohttp.ClientSession()

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    caption = message.caption or ""
    response_text = await gemini_service.ask_image(user_id, photo_bytes, "image/jpeg", caption, http_session)
    await message.answer(response_text, parse_mode="HTML", reply_markup=get_main_keyboard(lang))


@dp.message(F.audio)
async def handle_audio_message(message: types.Message):
    """Audio fayllarni Gemini AI orqali tinglab javob berish."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    audio_file = await bot.get_file(message.audio.file_id)
    import io
    audio_buffer = io.BytesIO()
    await bot.download_file(audio_file.file_path, destination=audio_buffer)
    audio_bytes = audio_buffer.getvalue()

    global http_session
    if not http_session or http_session.closed:
        http_session = aiohttp.ClientSession()

    await bot.send_chat_action(message.chat.id, ChatAction.RECORD_VOICE)
    mime = message.audio.mime_type or "audio/mp3"
    response_text = await gemini_service.ask_audio(user_id, audio_bytes, mime, http_session)

    tts_audio = await generate_voice_message(response_text)
    if tts_audio and os.path.exists(tts_audio):
        await message.answer_voice(
            voice=FSInputFile(tts_audio),
            caption="🔊 <i>Gemini AI javobi</i>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(lang)
        )
        try:
            os.remove(tts_audio)
        except Exception:
            pass
    else:
        await message.answer(response_text, parse_mode="HTML", reply_markup=get_main_keyboard(lang))


@dp.message(F.video)
async def handle_video_message(message: types.Message):
    """Videolarni saqlash haqida ma'lumot."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    await message.answer(
        tr("media_not_supported", lang),
        parse_mode="HTML",
        reply_markup=get_main_keyboard(lang)
    )


# ==========================================
# INLINE CALLBACK HANDLERS (DAVOMAT)
# ==========================================

@dp.callback_query(F.data == "att_today")
async def cb_att_today(call: types.CallbackQuery):
    """Bugungi davomat holati."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    att = get_today_attendance(user_id)

    if not att:
        await call.answer(tr("work_status_idle", lang), show_alert=True)
        return

    if att.get("status") == "working":
        # Hozirgacha ishlagan vaqt
        try:
            start_dt = datetime.strptime(f"{att['work_date']} {att['check_in_time']}", "%Y-%m-%d %H:%M:%S")
            diff = datetime.now() - start_dt
            mins = int(diff.total_seconds() // 60)
            elapsed = f"{mins // 60} soat {mins % 60} daqiqa"
        except Exception:
            elapsed = "aniqlanmoqda"
        text = tr("work_status_working", lang, check_in=att["check_in_time"][:5], elapsed=elapsed, method=att.get("method", "Wi-Fi"))
    else:
        mins = att.get("duration_minutes", 0)
        text = tr(
            "work_out_success", lang,
            check_in=att["check_in_time"][:5],
            check_out=att["check_out_time"][:5],
            hours=mins // 60,
            minutes=mins % 60
        )

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_attendance_inline_kb(lang))
    await call.answer()


@dp.callback_query(F.data == "att_monthly")
async def cb_att_monthly(call: types.CallbackQuery):
    """Oylik davomat hisoboti."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    text = generate_attendance_report_text(user_id)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_attendance_inline_kb(lang))
    except TelegramBadRequest:
        pass
    await call.answer()


@dp.callback_query(F.data == "att_wifi_help")
async def cb_att_wifi_help(call: types.CallbackQuery):
    """Wi-Fi avtomatizatsiyasini sozlash yo'riqnomasi."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    text = tr("wifi_guide_title", lang) + tr("wifi_guide_body", lang, token=BOT_TOKEN, chat_id=user_id)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_attendance_inline_kb(lang))
    await call.answer()


# ==========================================
# INLINE CALLBACK HANDLERS (HUJJATLAR)
# ==========================================

@dp.callback_query(F.data.startswith("docs_page:"))
async def cb_docs_page(call: types.CallbackQuery):
    """Hujjatlar ro'yxatini sahifalash."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    page = int(call.data.split(":")[1])

    docs, total_count = get_documents(user_id, page=page, per_page=5)
    if total_count == 0:
        await call.answer(tr("docs_empty", lang), show_alert=True)
        return

    text = tr("docs_title", lang, count=total_count)
    try:
        await call.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_documents_inline_kb(docs, page=page, total_count=total_count, lang=lang)
        )
    except TelegramBadRequest:
        pass
    await call.answer()


@dp.callback_query(F.data.startswith("doc_view:"))
async def cb_doc_view(call: types.CallbackQuery):
    """Bitta hujjat tafsilotlarini ko'rish."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    doc_id = int(call.data.split(":")[1])

    doc = get_document(doc_id, user_id)
    if not doc:
        await call.answer(tr("doc_not_found", lang), show_alert=True)
        return

    size_str = format_file_size(doc["file_size"])
    created_at = doc.get("created_at", "")[:16]
    caption_part = f"\n📝 <b>Izoh:</b> {doc['caption']}" if doc.get("caption") else ""

    text = (
        f"📄 <b>HUJJAT MA'LUMOTI</b>\n\n"
        f"• <b>Nomi:</b> <code>{doc['file_name']}</code>\n"
        f"• <b>Hajmi:</b> {size_str}\n"
        f"• <b>Kengaytmasi:</b> .{doc.get('file_ext', 'fayl')}\n"
        f"• <b>Sana:</b> {created_at}{caption_part}"
    )

    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_document_single_kb(doc_id, lang=lang))
    except TelegramBadRequest:
        pass
    await call.answer()


@dp.callback_query(F.data.startswith("doc_get:"))
async def cb_doc_get(call: types.CallbackQuery):
    """Hujjat faylini chatga yuborish."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    doc_id = int(call.data.split(":")[1])

    doc = get_document(doc_id, user_id)
    if not doc:
        await call.answer(tr("doc_not_found", lang), show_alert=True)
        return

    await bot.send_chat_action(call.message.chat.id, ChatAction.UPLOAD_DOCUMENT)
    try:
        await bot.send_document(
            chat_id=call.message.chat.id,
            document=doc["file_id"],
            caption=f"📄 {doc['file_name']}"
        )
        await call.answer()
    except Exception as e:
        logger.error("Hujjatni yuborishda xatolik: %s", e)
        await call.answer("Faylni yuklab bo'lmadi", show_alert=True)


@dp.callback_query(F.data.startswith("doc_del_confirm:"))
async def cb_doc_del_confirm(call: types.CallbackQuery):
    """Hujjatni o'chirish tasdiqlashini so'rash."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    doc_id = int(call.data.split(":")[1])

    text = tr("doc_del_confirm", lang)
    await call.message.edit_text(text, reply_markup=get_doc_delete_confirm_kb(doc_id, lang=lang))
    await call.answer()


@dp.callback_query(F.data.startswith("doc_del_yes:"))
async def cb_doc_del_yes(call: types.CallbackQuery):
    """Hujjatni butunlay o'chirish."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    doc_id = int(call.data.split(":")[1])

    success = delete_document(doc_id, user_id)
    if success:
        await call.answer(tr("doc_deleted", lang))
        # Yangilangan ro'yxatni ko'rsatamiz
        docs, total_count = get_documents(user_id, page=1, per_page=5)
        if total_count == 0:
            await call.message.edit_text(tr("docs_empty", lang))
        else:
            text = tr("docs_title", lang, count=total_count)
            await call.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=get_documents_inline_kb(docs, page=1, total_count=total_count, lang=lang)
            )
    else:
        await call.answer(tr("doc_not_found", lang), show_alert=True)


@dp.callback_query(F.data == "docs_search")
async def cb_docs_search(call: types.CallbackQuery):
    """Hujjat qidirish holatiga o'tkazish."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    ctx = get_user_ctx(user_id)
    ctx["state"] = "search_doc"

    await call.message.answer(
        tr("doc_search_prompt", lang),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(lang)
    )
    await call.answer()


# ==========================================
# INLINE CALLBACK HANDLERS (ESLATMALAR)
# ==========================================

@dp.callback_query(F.data == "rem_list")
async def cb_rem_list(call: types.CallbackQuery):
    """Eslatmalar ro'yxatini yangilash."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    rems = get_user_reminders(user_id, show_completed=False, limit=10)

    if not rems:
        await call.message.edit_text(
            tr("reminders_empty", lang),
            reply_markup=get_reminders_main_kb([], lang=lang)
        )
        return

    text = tr("reminders_title", lang, count=len(rems))
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_reminders_main_kb(rems, lang=lang)
    )
    await call.answer()


@dp.callback_query(F.data == "rem_new")
async def cb_rem_new(call: types.CallbackQuery):
    """Yangi eslatma yaratish so'rovi."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    ctx = get_user_ctx(user_id)
    ctx["state"] = "new_rem"

    await call.message.answer(
        tr("rem_new_prompt", lang),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(lang)
    )
    await call.answer()


@dp.callback_query(F.data.startswith("rem_view:"))
async def cb_rem_view(call: types.CallbackQuery):
    """Bitta eslatmani ko'rish."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    rem_id = int(call.data.split(":")[1])

    rems = get_user_reminders(user_id, show_completed=True, limit=50)
    target = next((r for r in rems if r["id"] == rem_id), None)

    if not target:
        await call.answer("Eslatma topilmadi", show_alert=True)
        return

    text = (
        f"⏰ <b>ESLATMA TAFSILOTI</b>\n\n"
        f"📌 <b>Vazifa:</b> {target['text']}\n"
        f"🕒 <b>Vaqti:</b> <code>{target['remind_at']}</code>\n"
        f"📊 <b>Holati:</b> {'Bajarilgan' if target['is_completed'] else 'Faol'}"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_reminder_item_kb(rem_id, lang=lang))
    await call.answer()


@dp.callback_query(F.data.startswith("rem_done:"))
async def cb_rem_done(call: types.CallbackQuery):
    """Eslatmani bajarildi deb belgilash."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    rem_id = int(call.data.split(":")[1])

    mark_reminder_completed(rem_id)
    await call.answer(tr("rem_done", lang))
    try:
        await call.message.edit_text(tr("rem_done", lang))
    except Exception:
        pass


@dp.callback_query(F.data.startswith("rem_snooze:"))
async def cb_rem_snooze(call: types.CallbackQuery):
    """Eslatmani 10 daqiqaga kechiktirish."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    rem_id = int(call.data.split(":")[1])

    snooze_reminder(rem_id, minutes=10)
    await call.answer(tr("rem_snoozed", lang))
    try:
        await call.message.edit_text(tr("rem_snoozed", lang))
    except Exception:
        pass


@dp.callback_query(F.data.startswith("rem_del:"))
async def cb_rem_del(call: types.CallbackQuery):
    """Eslatmani o'chirish."""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    rem_id = int(call.data.split(":")[1])

    delete_reminder(rem_id, user_id)
    await call.answer(tr("rem_deleted", lang))
    # Ro'yxatga qaytish
    rems = get_user_reminders(user_id, show_completed=False, limit=10)
    if not rems:
        await call.message.edit_text(tr("reminders_empty", lang))
    else:
        text = tr("reminders_title", lang, count=len(rems))
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_reminders_main_kb(rems, lang=lang))


@dp.callback_query(F.data == "noop")
async def cb_noop(call: types.CallbackQuery):
    """Bo'sh tugma."""
    await call.answer()


# ==========================================
# MATN VA OVOZLI XABARLARNI QAYTA ISHLASH
# ==========================================

@dp.message(F.text)
async def handle_text_messages(message: types.Message):
    """
    Foydalanuvchi matn yozganida (Qidiruv, Yangi eslatma yoki AI Chat).
    """
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    ctx = get_user_ctx(user_id)
    text = message.text.strip()

    # 1. Hujjat qidirish holati
    if ctx["state"] == "search_doc":
        ctx["state"] = None
        docs, total_count = get_documents(user_id, search_query=text, page=1, per_page=5)
        if total_count == 0:
            await message.answer(
                f"«{text}» bo'yicha hech qanday hujjat topilmadi.",
                reply_markup=get_main_keyboard(lang)
            )
            return
        res_title = tr("doc_search_results", lang, query=text)
        await message.answer(
            f"{res_title}\nJami: {total_count} ta",
            parse_mode="HTML",
            reply_markup=get_documents_inline_kb(docs, page=1, total_count=total_count, lang=lang)
        )
        return

    # 2. Yangi eslatma yaratish holati yoki tabiiy eslatma matni
    if ctx["state"] == "new_rem":
        ctx["state"] = None
        parsed_dt = parse_reminder_time(text)

        if not parsed_dt:
            # Agar faqat vaqt yozilmagan bo'lsa, xabarning boshini yoki oxirini tekshiramiz
            parsed_dt = datetime.now() + timedelta(hours=1)
            rem_text = text
        else:
            # Vaqt topildi, matndan vaqt qismini tozalash
            rem_text = text

        dt_str = parsed_dt.strftime("%Y-%m-%d %H:%M:%S")
        add_reminder(user_id, rem_text, dt_str)

        await message.answer(
            tr("rem_saved", lang, text=rem_text, time=format_datetime(parsed_dt, lang)),
            parse_mode="HTML",
            reply_markup=get_main_keyboard(lang)
        )
        return

    # 3. Agar eslatmaga o'xshash bo'lsa (masalan: "15:00 da majlis")
    parsed_dt = parse_reminder_time(text)
    if parsed_dt and (parsed_dt - datetime.now()).total_seconds() > 60:
        dt_str = parsed_dt.strftime("%Y-%m-%d %H:%M:%S")
        add_reminder(user_id, text, dt_str)
        await message.answer(
            tr("rem_saved", lang, text=text, time=format_datetime(parsed_dt, lang)),
            parse_mode="HTML",
            reply_markup=get_main_keyboard(lang)
        )
        return

    # 4. DOIMIY VA AVTOMATIK AI CHAT REJIMI
    # Har qanday erkin savol yoki murojaat to'g'ridan-to'g'ri Gemini AI ga yuboriladi!
    global http_session
    if not http_session or http_session.closed:
        http_session = aiohttp.ClientSession()

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    loc_info = get_user_current_location(user_id)
    response = await gemini_service.ask(user_id, text, http_session, location_info=loc_info)
    await message.answer(response, parse_mode="HTML", reply_markup=get_main_keyboard(lang))


@dp.message(F.voice)
async def handle_voice_message(message: types.Message):
    """Ovozli xabarlarni AI rejimida qabul qilish."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    ctx = get_user_ctx(user_id)

    ctx["mode"] = "ai_chat"

    # Ovozli xabarni yuklab olish
    voice_file = await bot.get_file(message.voice.file_id)
    import io
    voice_buffer = io.BytesIO()
    await bot.download_file(voice_file.file_path, destination=voice_buffer)
    audio_bytes = voice_buffer.getvalue()

    global http_session
    if not http_session or http_session.closed:
        http_session = aiohttp.ClientSession()

    await bot.send_chat_action(message.chat.id, ChatAction.RECORD_VOICE)
    # Gemini AI ovozli xabarni eshitib javob qaytaradi
    loc_info = get_user_current_location(user_id)
    response_text = await gemini_service.ask_audio(user_id, audio_bytes, "audio/ogg", http_session, location_info=loc_info)

    # Javobni ovozli qilib qaytaramiz
    tts_audio = await generate_voice_message(response_text)
    if tts_audio and os.path.exists(tts_audio):
        await message.answer_voice(
            voice=FSInputFile(tts_audio),
            caption="🔊 <i>Gemini AI javobi</i>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(lang)
        )
        try:
            os.remove(tts_audio)
        except Exception:
            pass
    else:
        await message.answer(response_text, parse_mode="HTML")


# ==========================================
# FON REJIMIDAGI ESLATMA VA WI-FI SERVER
# ==========================================

async def reminders_worker():
    """Vaqti kelgan eslatmalarni fon rejimida tekshirib boruvchi sikl."""
    logger.info("Eslatmalar fon xizmati ishga tushdi.")
    while True:
        try:
            due_items = get_due_reminders()
            for item in due_items:
                r_id = item["id"]
                u_id = item["user_id"]
                r_text = item["text"]
                r_time = item["remind_at"][11:16]
                lang = get_user_lang(u_id)

                alert_text = tr("rem_alert", lang, text=r_text, time=r_time)
                try:
                    await bot.send_message(
                        chat_id=u_id,
                        text=alert_text,
                        parse_mode="HTML",
                        reply_markup=get_reminder_alert_kb(r_id, lang=lang)
                    )
                    # Bajarildi deb belgilaymiz
                    mark_reminder_completed(r_id, repeat=item.get("repeat", "none"))
                except Exception as e:
                    logger.warning("Eslatmani yuborishda xatolik (user %s): %s", u_id, e)

        except Exception as e:
            logger.error("Eslatmalar tekshirishda xatolik: %s", e)

        await asyncio.sleep(25)


async def wifi_webhook_handler(request: web.Request) -> web.Response:
    """
    Mahalliy Wi-Fi tarmoqdan telefon yuborgan signalni qabul qiluvchi HTTP endpoint:
    GET /wifi?action=in
    GET /wifi?action=out
    """
    action = request.query.get("action", "").lower().strip()
    user_id_param = request.query.get("user_id", "").strip()

    target_user_id = int(user_id_param) if user_id_param.isdigit() else (int(ADMIN_ID) if ADMIN_ID and ADMIN_ID.isdigit() else None)

    if not target_user_id:
        return web.json_response({"ok": False, "error": "User ID topilmadi"}, status=400)

    logger.info("Wi-Fi signal qabul qilindi: action=%s, user=%s", action, target_user_id)

    if action in ["in", "arrived", "connect"]:
        msg = await process_check_in(target_user_id, method="📶 Wi-Fi avtomat")
        try:
            lang = get_user_lang(target_user_id)
            await bot.send_message(chat_id=target_user_id, text=msg, parse_mode="HTML", reply_markup=get_main_keyboard(lang))
        except Exception as e:
            logger.error("Wi-Fi xabarini yuborishda xatolik: %s", e)
        return web.json_response({"ok": True, "action": "in", "message": msg})

    elif action in ["out", "left", "disconnect"]:
        msg = await process_check_out(target_user_id, method="📶 Wi-Fi avtomat")
        try:
            lang = get_user_lang(target_user_id)
            await bot.send_message(chat_id=target_user_id, text=msg, parse_mode="HTML", reply_markup=get_main_keyboard(lang))
        except Exception as e:
            logger.error("Wi-Fi xabarini yuborishda xatolik: %s", e)
        return web.json_response({"ok": True, "action": "out", "message": msg})

    return web.json_response({"ok": False, "error": "action parametri 'in' yoki 'out' bo'lishi kerak"}, status=400)


async def dashboard_handler(request: web.Request) -> web.Response:
    """Minimalistik bej va jigarrang web boshqaruv paneli."""
    dashboard_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")
    if os.path.exists(dashboard_path):
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html")
    return web.Response(text="Dashboard sahifasi topilmadi", status=404)


async def api_status_handler(request: web.Request) -> web.Response:
    """Dashboard uchun joriy davomat JSON API si."""
    target_user_id = int(ADMIN_ID) if ADMIN_ID and ADMIN_ID.isdigit() else 0
    today = get_today_attendance(target_user_id)
    now = datetime.now()
    rows, summary = get_monthly_attendance(target_user_id, now.year, now.month)
    return web.json_response({
        "today": today,
        "summary": summary
    })


async def start_wifi_http_server():
    """Mahalliy tarmoqda Wi-Fi ulanishlarini kutuvchi mini server va Web App."""
    app = web.Application()
    app.router.add_get("/", dashboard_handler)
    app.router.add_get("/dashboard", dashboard_handler)
    app.router.add_get("/api/status", api_status_handler)
    app.router.add_get("/wifi", wifi_webhook_handler)
    app.router.add_post("/wifi", wifi_webhook_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=WIFI_PORT)
    try:
        await site.start()
        logger.info("Wi-Fi va Web App serveri ishga tushdi: http://localhost:%s", WIFI_PORT)
    except Exception as e:
        logger.warning("Wi-Fi serverini ishga tushirishda xatolik (port band bo'lishi mumkin): %s", e)


# ==========================================
# ASOSIY ISHGA TUSHIRISH (MAIN)
# ==========================================

async def main():
    """Botni to'liq ishga tushirish funksiyasi."""
    global http_session
    http_session = aiohttp.ClientSession()

    # Bot buyruqlarini Telegram menyusiga o'rnatish (stikerlarsiz)
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni qayta ishga tushirish"),
        BotCommand(command="qayerdaman", description="Hozirgi ko'changizni bilish (Radar)"),
        BotCommand(command="voice", description="Ovozli ogohlantirishni yoqish/o'chirish"),
        BotCommand(command="security", description="Xavfsizlik va himoya holati"),
        BotCommand(command="ai", description="AI shaxsiy maslahatchi")
    ])

    # Fon rejimida eslatmalar tekshiruvchisini ishga tushirish
    asyncio.create_task(reminders_worker())

    # Fon rejimida mahalliy Wi-Fi serverini ishga tushirish
    # asyncio.create_task(start_wifi_http_server())  # Ofis botiga ko'chirildi

    logger.info("Bot muvaffaqiyatli ishga tushdi. Xabarlar kutilmoqda...")

    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        if http_session and not http_session.closed:
            await http_session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
