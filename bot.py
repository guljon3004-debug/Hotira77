# -*- coding: utf-8 -*-
import os
import sys
import re
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
import aiohttp

# Windows konsolida UTF-8 to'g'ri ko'rinishi uchun
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from aiogram import Bot, Dispatcher, types, F
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
    DOWNLOADS_DIR,
    validate_config
)
from locales import tr
from database import (
    init_db,
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
    log_security_incident
)
from reminder_helper import parse_reminder_time, format_datetime
from keyboards import (
    get_main_keyboard,
    get_cancel_keyboard,
    get_ai_mode_keyboard,
    get_reminders_main_kb,
    get_reminder_item_kb,
    get_reminder_alert_kb,
    get_documents_inline_kb,
    get_document_single_kb,
    get_doc_delete_confirm_kb,
    get_settings_keyboard,
    get_language_inline_kb
)
from ai_chat import gemini_service
from tts_service import generate_voice_message
from card_generator import (
    generate_welcome_card,
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
logger = logging.getLogger("Hotira77")

# Konfiguratsiyani tekshirish
validate_config()

# Bot va Dispatcher obyektlari
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Global aiohttp sessiyasi
http_session: aiohttp.ClientSession | None = None

# Foydalanuvchilar holati (FSM alternativi): user_id -> dict
user_context: dict[int, dict] = {}


def get_user_ctx(user_id: int) -> dict:
    """Foydalanuvchi joriy holat kontekstini oladi."""
    if user_id not in user_context:
        user_context[user_id] = {
            "state": None,
            "rem_text": None,
            "doc_search": None
        }
    return user_context[user_id]


async def is_authorized(event: types.Message | types.CallbackQuery) -> bool:
    """Foydalanuvchi bot egasi ekanligini qat'iy tekshiradi."""
    user = event.from_user
    if not user:
        return False
    user_id = user.id

    admin_str = str(ADMIN_ID or "").strip()
    if admin_str and admin_str != "0":
        try:
            admin_int = int(admin_str)
            if user_id != admin_int:
                log_security_incident(
                    user_id=user_id,
                    username=user.username or "",
                    full_name=user.full_name or "",
                    action_attempted="unauthorized_access",
                    details=f"Begona foydalanuvchi botga kirishga urindi (ID: {user_id})"
                )
                lang = get_user_lang(user_id)
                msg = tr("unauthorized", lang)
                if isinstance(event, types.Message):
                    await event.answer(msg, parse_mode="HTML")
                else:
                    await event.answer(msg, show_alert=True)
                return False
        except ValueError:
            pass

    return True


# ==========================================
# FON REJIMIDAGI ESLATMALAR TEKSHIRUVCHISI
# ==========================================

async def reminders_worker():
    """Har 15 soniyada eslatmalarni tekshirib, egasiga yuboradi."""
    logger.info("Eslatmalar tekshiruvchi fon xizmati ishga tushdi.")
    while True:
        try:
            due = get_due_reminders()
            for r in due:
                r_id = r["id"]
                u_id = r["user_id"]
                text = r["text"]
                lang = get_user_lang(u_id)

                alert_text = tr("rem_alert", lang, text=text)
                kb = get_reminder_alert_kb(r_id, lang)

                try:
                    await bot.send_message(
                        chat_id=u_id,
                        text=alert_text,
                        parse_mode="HTML",
                        reply_markup=kb
                    )

                    # Agar ovozli ogohlantirish yoqilgan bo'lsa
                    if is_voice_enabled(u_id):
                        voice_text = f"Eslatma vaqti keldi: {text}"
                        voice_path = await generate_voice_message(voice_text)
                        if voice_path and os.path.exists(voice_path):
                            await bot.send_voice(
                                chat_id=u_id,
                                voice=FSInputFile(voice_path),
                                caption=f"⏰ <i>{text}</i>",
                                parse_mode="HTML"
                            )
                except Exception as send_err:
                    logger.warning("Eslatmani yuborishda xatolik (ID %s): %s", r_id, send_err)

                mark_reminder_completed(r_id)
        except Exception as e:
            logger.error("Reminders worker xatosi: %s", e)

        await asyncio.sleep(15)


# ==========================================
# /START VA ASOSIY BUYRUQLAR
# ==========================================

@dp.message(CommandStart())
async def handle_start(message: types.Message):
    """Start buyrug'i (Muqova kartochkasi va toza menyu)."""
    if not await is_authorized(message):
        return

    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    ctx = get_user_ctx(user_id)
    ctx["state"] = None

    name = message.from_user.full_name
    title = tr("start_title", lang, name=name)
    desc = tr("start_desc", lang)

    os.makedirs("downloads", exist_ok=True)
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


@dp.message(F.text.in_(["🏠 Asosiy menyu", "🏠 Главное меню", "/menu"]))
async def handle_back_main(message: types.Message):
    """Asosiy menyuga qaytish."""
    if not await is_authorized(message):
        return
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    ctx = get_user_ctx(user_id)
    ctx["state"] = None
    await message.answer("🏠 Asosiy menyu:", reply_markup=get_main_keyboard(lang))


@dp.message(F.text.in_(["❌ Bekor qilish", "❌ Отмена", "/cancel"]))
async def handle_cancel(message: types.Message):
    """Joriy amalni bekor qilish."""
    if not await is_authorized(message):
        return
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    ctx = get_user_ctx(user_id)
    ctx["state"] = None
    await message.answer("Amal bekor qilindi.", reply_markup=get_main_keyboard(lang))


# ==========================================
# 🚗 JONLI KO'CHALAR RADARI (LOCATION)
# ==========================================

@dp.message(F.text.func(lambda t: bool(t and ("AVTO-RADAR" in t or "АВТО-РАДАР" in t))))
async def handle_radar_button(message: types.Message):
    """Radar tugmasi bosilganda ma'lumot berish."""
    if not await is_authorized(message):
        return
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    loc = get_user_current_location(user_id)
    if loc:
        road = loc.get("road") or "Aniqlanmoqda"
        district = loc.get("district") or loc.get("city") or "Toshkent"
        time_str = loc.get("updated_at", datetime.now()).strftime("%H:%M:%S")
        cur_text = tr("loc_current", lang, road=road, district=district, time=time_str)
        await message.answer(f"{cur_text}\n\n{tr('radar_info', lang)}", parse_mode="HTML", reply_markup=get_main_keyboard(lang))
    else:
        await message.answer(tr("radar_info", lang), parse_mode="HTML", reply_markup=get_main_keyboard(lang))


@dp.message(Command("qayerdaman"))
@dp.message(F.text.func(lambda t: bool(t and any(k in t.lower() for k in ["qayerdaman", "qayerda turibman", "qaysi kochadaman", "qaysi ko'chadaman", "где я", "какая улица", "қайердаман"]))))
async def handle_where_am_i(message: types.Message):
    """Qayerdaman savoliga javob berish."""
    if not await is_authorized(message):
        return
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    loc_data = get_user_current_location(user_id)

    if not loc_data:
        await message.answer(tr("radar_info", lang), parse_mode="HTML", reply_markup=get_main_keyboard(lang))
        return

    road = loc_data.get("road") or "Ko'cha aniqlanmoqda"
    district = loc_data.get("district") or loc_data.get("city") or "Toshkent"
    time_str = loc_data.get("updated_at", datetime.now()).strftime("%H:%M:%S")

    text = tr("loc_current", lang, road=road, district=district, time=time_str)

    os.makedirs("downloads", exist_ok=True)
    card_path = f"downloads/loc_{user_id}.png"
    try:
        generate_location_card(road=road, district=district, time_str=time_str, output_path=card_path)
        if os.path.exists(card_path):
            await message.answer_photo(
                photo=FSInputFile(card_path),
                caption=text,
                parse_mode="HTML",
                reply_markup=get_main_keyboard(lang)
            )
            return
    except Exception as e:
        logger.warning("Joylashuv kartochkasi xatosi: %s", e)

    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(lang))


@dp.message(F.location)
@dp.edited_message(F.location)
async def handle_location_update(message: types.Message):
    """Jonli geolokatsiya (Live Location) va oddiy joylashuvni qabul qilish."""
    if not await is_authorized(message):
        return

    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    loc = message.location
    lat, lon = loc.latitude, loc.longitude

    prev = get_user_current_location(user_id)
    if prev:
        dist = calculate_distance_meters(prev["lat"], prev["lon"], lat, lon)
        if dist < 20:
            return

    global http_session
    if not http_session or http_session.closed:
        http_session = aiohttp.ClientSession()

    addr = await resolve_address(lat, lon, http_session)
    old_road = prev.get("road") if prev else None
    new_road = addr.get("road")
    district = addr.get("district") or addr.get("city") or "Toshkent"
    time_str = datetime.now().strftime("%H:%M:%S")

    is_live = bool(getattr(loc, 'live_period', None))

    # Ko'cha o'zgarishini tekshirish
    if old_road and new_road and old_road.lower() != new_road.lower() and new_road.lower() != "aniqlanmoqda":
        logger.info(f"Ko'cha o'zgardi [user: {user_id}]: {old_road} -> {new_road}")

        # 1. Madina ovozida audio xabar tayyorlash
        voice_text = f"Siz {old_road}dan {new_road}ga o'tdingiz."
        voice_path = await generate_voice_message(voice_text)

        # 2. Rasm kartochkasi
        os.makedirs("downloads", exist_ok=True)
        change_card_path = f"downloads/change_{user_id}_{int(datetime.now().timestamp())}.png"
        sent_card = False
        try:
            generate_street_change_card(
                old_street=old_road,
                new_street=new_road,
                district=district,
                time_str=time_str,
                output_path=change_card_path
            )
            if os.path.exists(change_card_path):
                caption_msg = (
                    f"🚗 <b>KO'CHA O'ZGARDI!</b>\n\n"
                    f"Avvalgi ko'cha: <s>{old_road}</s>\n"
                    f"Yangi ko'cha: <b>{new_road}</b>\n"
                    f"Hudud: <i>{district}</i>\n"
                    f"Vaqt: <code>{time_str}</code>"
                )
                await message.answer_photo(
                    photo=FSInputFile(change_card_path),
                    caption=caption_msg,
                    parse_mode="HTML"
                )
                sent_card = True
        except Exception as card_err:
            logger.warning("Ko'cha o'zgarishi kartochkasida xatolik: %s", card_err)

        if not sent_card:
            await message.answer(
                f"🚗 <b>KO'CHA O'ZGARDI!</b>\n\n"
                f"Avvalgi: <s>{old_road}</s>\n"
                f"Yangi ko'cha: <b>{new_road}</b> ({district})",
                parse_mode="HTML"
            )

        # 3. Ovozli xabarni yuborish
        if voice_path and os.path.exists(voice_path):
            try:
                await message.answer_voice(
                    voice=FSInputFile(voice_path),
                    caption=f"🎙 <i>{voice_text}</i>",
                    parse_mode="HTML"
                )
            except Exception as v_err:
                logger.warning("Ovozli xabarni jo'natishda xatolik: %s", v_err)

    elif not prev:
        # Birinchi marta joylashuv yuborilganda xabar
        cur_text = tr("loc_current", lang, road=(new_road or "Aniqlanmoqda"), district=district, time=time_str)
        await message.answer(
            f"📍 <b>Joylashuvingiz qabul qilindi!</b>\n\n{cur_text}\n\n"
            f"<i>Avtomobilda ketayotganingizda yangi ko'chaga o'tsangiz, bot avtomatik ovoz chiqarib aytib turadi.</i>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(lang)
        )

    update_user_location(user_id, lat, lon, addr, is_live=is_live)


# ==========================================
# ⏰ AQLLI ESLATMALAR (REMINDERS)
# ==========================================

@dp.message(F.text.func(lambda t: bool(t and ("Eslatmalar" in t or "Напоминания" in t))))
async def handle_reminders_button(message: types.Message):
    """Eslatmalar ro'yxatini ko'rsatish."""
    if not await is_authorized(message):
        return
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    rems = get_user_reminders(user_id)
    if not rems:
        await message.answer(
            tr("no_reminders", lang),
            parse_mode="HTML",
            reply_markup=get_reminders_main_kb([], lang)
        )
    else:
        await message.answer(
            tr("reminders_title", lang),
            parse_mode="HTML",
            reply_markup=get_reminders_main_kb(rems, lang)
        )


@dp.callback_query(F.data == "rem_list")
async def cb_rem_list(call: types.CallbackQuery):
    """Eslatmalar ro'yxatiga qaytish."""
    if not await is_authorized(call):
        return
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    rems = get_user_reminders(user_id)
    await call.message.edit_text(
        tr("reminders_title", lang),
        parse_mode="HTML",
        reply_markup=get_reminders_main_kb(rems, lang)
    )
    await call.answer()


@dp.callback_query(F.data == "rem_new")
async def cb_rem_new(call: types.CallbackQuery):
    """Yangi eslatma qo'shish so'rovi."""
    if not await is_authorized(call):
        return
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    ctx = get_user_ctx(user_id)
    ctx["state"] = "waiting_rem_text"

    await call.message.answer(
        tr("prompt_rem_text", lang),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(lang)
    )
    await call.answer()


@dp.callback_query(F.data.startswith("rem_view:"))
async def cb_rem_view(call: types.CallbackQuery):
    """Bitta eslatmani ko'rish."""
    if not await is_authorized(call):
        return
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    r_id = int(call.data.split(":")[1])

    rems = get_user_reminders(user_id)
    target = next((r for r in rems if r["id"] == r_id), None)
    if not target:
        await call.answer("Eslatma topilmadi", show_alert=True)
        return

    text_msg = (
        f"⏰ <b>ESLATMA TAFSILOTI</b>\n\n"
        f"📝 Matn: <b>{target['text']}</b>\n"
        f"📅 Vaqt: <code>{target['remind_at']}</code>\n"
        f"Holat: <i>{'Kutilmoqda' if target.get('status') == 'pending' else 'Bajarilgan'}</i>"
    )
    await call.message.edit_text(
        text_msg,
        parse_mode="HTML",
        reply_markup=get_reminder_item_kb(r_id, lang)
    )
    await call.answer()


@dp.callback_query(F.data.startswith("rem_done:"))
async def cb_rem_done(call: types.CallbackQuery):
    """Eslatmani bajarildi deb belgilash."""
    if not await is_authorized(call):
        return
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    r_id = int(call.data.split(":")[1])
    mark_reminder_completed(r_id)

    rems = get_user_reminders(user_id)
    await call.message.edit_text(
        f"{tr('rem_done_msg', lang)}\n\n{tr('reminders_title', lang)}",
        parse_mode="HTML",
        reply_markup=get_reminders_main_kb(rems, lang)
    )
    await call.answer(tr("rem_done_msg", lang))


@dp.callback_query(F.data.startswith("rem_del:"))
async def cb_rem_del(call: types.CallbackQuery):
    """Eslatmani o'chirish."""
    if not await is_authorized(call):
        return
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    r_id = int(call.data.split(":")[1])
    delete_reminder(r_id)

    rems = get_user_reminders(user_id)
    await call.message.edit_text(
        f"{tr('rem_deleted', lang)}\n\n{tr('reminders_title', lang)}",
        parse_mode="HTML",
        reply_markup=get_reminders_main_kb(rems, lang)
    )
    await call.answer(tr("rem_deleted", lang))


@dp.callback_query(F.data.startswith("rem_snooze:"))
async def cb_rem_snooze(call: types.CallbackQuery):
    """Eslatmani 10 daqiqaga kechiktirish."""
    if not await is_authorized(call):
        return
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    r_id = int(call.data.split(":")[1])
    snooze_reminder(r_id, minutes=10)

    await call.message.edit_text(tr("rem_snoozed", lang), parse_mode="HTML")
    await call.answer(tr("rem_snoozed", lang))


# ==========================================
# 📁 SHAXSIY SEYF VA HUJJATLAR (DOCUMENTS)
# ==========================================

@dp.message(F.text.func(lambda t: bool(t and ("Shaxsiy Seyf" in t or "Личный Сейф" in t or "Hujjatlar" in t))))
async def handle_documents_button(message: types.Message):
    """Shaxsiy Seyfdagi fayllarni ko'rsatish."""
    if not await is_authorized(message):
        return
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    docs = get_documents(user_id)
    if not docs:
        await message.answer(
            f"{tr('docs_title', lang)}\n\n{tr('no_docs', lang)}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(lang)
        )
    else:
        await message.answer(
            tr("docs_title", lang),
            parse_mode="HTML",
            reply_markup=get_documents_inline_kb(docs, lang)
        )


@dp.callback_query(F.data == "doc_list")
async def cb_doc_list(call: types.CallbackQuery):
    """Hujjatlar ro'yxatiga qaytish."""
    if not await is_authorized(call):
        return
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    docs = get_documents(user_id)
    await call.message.edit_text(
        tr("docs_title", lang),
        parse_mode="HTML",
        reply_markup=get_documents_inline_kb(docs, lang)
    )
    await call.answer()


@dp.callback_query(F.data.startswith("doc_view:"))
async def cb_doc_view(call: types.CallbackQuery):
    """Bitta hujjat ma'lumotlarini ko'rish."""
    if not await is_authorized(call):
        return
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    d_id = int(call.data.split(":")[1])
    doc = get_document(d_id)
    if not doc:
        await call.answer("Fayl topilmadi", show_alert=True)
        return

    size_kb = f"{doc['file_size'] / 1024:.1f} KB" if doc.get('file_size') else "Noma'lum"
    text = (
        f"📄 <b>HUJJAT MA'LUMOTI</b>\n\n"
        f"🏷 Nomi: <code>{doc['file_name']}</code>\n"
        f"📦 Hajmi: {size_kb}\n"
        f"📅 Saqlangan vaqt: <code>{doc.get('uploaded_at', '')}</code>"
    )
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_document_single_kb(d_id, lang)
    )
    await call.answer()


@dp.callback_query(F.data.startswith("doc_get:"))
async def cb_doc_download(call: types.CallbackQuery):
    """Faylni foydalanuvchiga qayta yuborish."""
    if not await is_authorized(call):
        return
    d_id = int(call.data.split(":")[1])
    doc = get_document(d_id)
    if not doc:
        await call.answer("Fayl topilmadi", show_alert=True)
        return

    file_path = doc.get("file_path")
    if file_path and os.path.exists(file_path):
        await call.message.answer_document(
            document=FSInputFile(file_path, filename=doc["file_name"]),
            caption=f"📁 <i>{doc['file_name']}</i>",
            parse_mode="HTML"
        )
        await call.answer("Fayl yuborildi")
    else:
        # Agar lokal yo'q bo'lsa, Telegram file_id orqali yuborish
        try:
            await call.message.answer_document(
                document=doc["file_id"],
                caption=f"📁 <i>{doc['file_name']}</i>",
                parse_mode="HTML"
            )
            await call.answer("Fayl yuborildi")
        except Exception as e:
            await call.answer(f"Faylni ochishda xatolik: {e}", show_alert=True)


@dp.callback_query(F.data.startswith("doc_del_ask:"))
async def cb_doc_del_ask(call: types.CallbackQuery):
    """Hujjatni o'chirish tasdig'i."""
    if not await is_authorized(call):
        return
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    d_id = int(call.data.split(":")[1])
    await call.message.edit_text(
        "🗑 <b>Ushbu faylni o'chirishga ishonchingiz komilmi?</b>",
        parse_mode="HTML",
        reply_markup=get_doc_delete_confirm_kb(d_id, lang)
    )
    await call.answer()


@dp.callback_query(F.data.startswith("doc_del_confirm:"))
async def cb_doc_del_confirm(call: types.CallbackQuery):
    """Hujjatni o'chirish."""
    if not await is_authorized(call):
        return
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    d_id = int(call.data.split(":")[1])
    doc = get_document(d_id)
    if doc and doc.get("file_path") and os.path.exists(doc["file_path"]):
        try:
            os.remove(doc["file_path"])
        except Exception:
            pass
    delete_document(d_id)

    docs = get_documents(user_id)
    await call.message.edit_text(
        f"🗑 <b>Fayl o'chirildi.</b>\n\n{tr('docs_title', lang)}",
        parse_mode="HTML",
        reply_markup=get_documents_inline_kb(docs, lang)
    )
    await call.answer("Fayl o'chirildi")


@dp.message(F.document | F.photo | F.video | F.audio)
async def handle_incoming_file(message: types.Message):
    """Har qanday yuborilgan faylni Seyfga saqlash."""
    if not await is_authorized(message):
        return

    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    os.makedirs("storage", exist_ok=True)

    file_id = None
    file_name = "fayl"
    file_size = 0
    file_type = "document"

    if message.document:
        doc = message.document
        file_id = doc.file_id
        file_name = doc.file_name or f"doc_{int(datetime.now().timestamp())}"
        file_size = doc.file_size or 0
        file_type = "document"
    elif message.photo:
        p = message.photo[-1]
        file_id = p.file_id
        file_name = f"photo_{int(datetime.now().timestamp())}.jpg"
        file_size = p.file_size or 0
        file_type = "photo"
    elif message.video:
        v = message.video
        file_id = v.file_id
        file_name = v.file_name or f"video_{int(datetime.now().timestamp())}.mp4"
        file_size = v.file_size or 0
        file_type = "video"
    elif message.audio:
        a = message.audio
        file_id = a.file_id
        file_name = a.file_name or f"audio_{int(datetime.now().timestamp())}.mp3"
        file_size = a.file_size or 0
        file_type = "audio"

    if not file_id:
        return

    local_path = os.path.join("storage", f"{uuid.uuid4().hex[:8]}_{file_name}")
    try:
        f_info = await bot.get_file(file_id)
        await bot.download_file(f_info.file_path, destination=local_path)
    except Exception as down_err:
        logger.warning("Faylni yuklab olishda xatolik (faqat ID saqlanadi): %s", down_err)
        local_path = ""

    add_document(
        user_id=user_id,
        file_id=file_id,
        file_name=file_name,
        file_size=file_size,
        file_type=file_type,
        file_path=local_path
    )

    size_str = f"{file_size / 1024:.1f} KB" if file_size else "Noma'lum"
    confirm_msg = tr("doc_saved", lang, name=file_name, size=size_str, type=file_type)
    await message.answer(confirm_msg, parse_mode="HTML", reply_markup=get_main_keyboard(lang))


# ==========================================
# ⚙️ SOZLAMALAR VA TIL
# ==========================================

@dp.message(F.text.func(lambda t: bool(t and ("Sozlamalar" in t or "Настройки" in t or t == "/settings"))))
async def handle_settings_button(message: types.Message):
    """Sozlamalar menyusi."""
    if not await is_authorized(message):
        return
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    v_on = is_voice_enabled(user_id)
    text = f"{tr('settings_title', lang)}\n\n" + (tr('voice_on', lang) if v_on else tr('voice_off', lang))
    await message.answer(text, parse_mode="HTML", reply_markup=get_settings_keyboard(lang, v_on))


@dp.callback_query(F.data == "toggle_voice")
async def cb_toggle_voice(call: types.CallbackQuery):
    """Ovozli javobni yoqish/o'chirish."""
    if not await is_authorized(call):
        return
    user_id = call.from_user.id
    lang = get_user_lang(user_id)
    current = is_voice_enabled(user_id)
    new_state = not current
    set_voice_enabled(user_id, new_state)

    text = f"{tr('settings_title', lang)}\n\n" + (tr('voice_on', lang) if new_state else tr('voice_off', lang))
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_settings_keyboard(lang, new_state))
    status_str = "yoqildi" if new_state else "o'chirildi"
    await call.answer(f"Ovoz {status_str}")


@dp.callback_query(F.data == "show_lang_kb")
async def cb_show_lang(call: types.CallbackQuery):
    """Til tanlash oynasi."""
    if not await is_authorized(call):
        return
    await call.message.edit_text("🌐 Tilni tanlang / Выберите язык:", reply_markup=get_language_inline_kb())
    await call.answer()


@dp.callback_query(F.data.startswith("set_lang:"))
async def cb_set_lang(call: types.CallbackQuery):
    """Tilni saqlash."""
    if not await is_authorized(call):
        return
    user_id = call.from_user.id
    new_lang = call.data.split(":")[1]
    set_user_lang(user_id, new_lang)
    v_on = is_voice_enabled(user_id)

    text = f"{tr('settings_title', new_lang)}\n\n" + (tr('voice_on', new_lang) if v_on else tr('voice_off', new_lang))
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_settings_keyboard(new_lang, v_on))
    await call.message.answer(
        "✅ Til o'zgartirildi / Язык успешно изменен.",
        reply_markup=get_main_keyboard(new_lang)
    )
    await call.answer()


@dp.message(Command("voice"))
async def cmd_voice(message: types.Message):
    """Ovozni tezkor yoqish/o'chirish."""
    if not await is_authorized(message):
        return
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    current = is_voice_enabled(user_id)
    set_voice_enabled(user_id, not current)
    status = "yoqildi" if not current else "o'chirildi"
    await message.answer(f"Ovozli ogohlantirish {status}.", reply_markup=get_main_keyboard(lang))


# ==========================================
# 🤖 GEMINI AI CHAT VA MATN / OVOZ MULOQOT
# ==========================================

@dp.message(F.text.func(lambda t: bool(t and ("AI Maslahatchi" in t or "AI Помощник" in t or t == "/ai"))))
async def handle_ai_button(message: types.Message):
    """AI Maslahatchi bosh menyusi."""
    if not await is_authorized(message):
        return
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    await message.answer(
        tr("ai_title", lang),
        parse_mode="HTML",
        reply_markup=get_ai_mode_keyboard(lang)
    )


@dp.message(F.text.func(lambda t: bool(t and ("Suhbatni tozalash" in t or "Очистить чат" in t))))
async def handle_clear_ai(message: types.Message):
    """AI suhbat kontekstini tozalash."""
    if not await is_authorized(message):
        return
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    gemini_service.clear_history(user_id)
    await message.answer(tr("chat_cleared", lang), parse_mode="HTML", reply_markup=get_main_keyboard(lang))


@dp.message(F.voice)
async def handle_voice_message(message: types.Message):
    """Ovozli xabarlarni AI orqali tahlil qilib, ovozda javob qaytarish."""
    if not await is_authorized(message):
        return

    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    await bot.send_chat_action(chat_id=user_id, action=ChatAction.RECORD_VOICE)

    os.makedirs("downloads", exist_ok=True)
    voice_path = os.path.join("downloads", f"voice_{user_id}_{message.voice.file_id[:8]}.ogg")
    try:
        f_info = await bot.get_file(message.voice.file_id)
        await bot.download_file(f_info.file_path, destination=voice_path)
        with open(voice_path, "rb") as vf:
            audio_bytes = vf.read()
    except Exception as e:
        logger.error("Ovozli faylni yuklab olishda xatolik: %s", e)
        await message.answer("Ovozli xabarni qabul qilishda xatolik yuz berdi.")
        return

    global http_session
    if not http_session or http_session.closed:
        http_session = aiohttp.ClientSession()

    loc_info = get_user_current_location(user_id)
    ai_answer = await gemini_service.ask_audio(
        user_id=user_id,
        audio_bytes=audio_bytes,
        mime_type="audio/ogg",
        session=http_session,
        location_info=loc_info
    )

    # Javobni ovozli qilib jo'natamiz
    tts_audio = await generate_voice_message(ai_answer)
    if tts_audio and os.path.exists(tts_audio):
        await message.answer_voice(
            voice=FSInputFile(tts_audio),
            caption=f"🎙 <i>{ai_answer[:200]}</i>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(lang)
        )
    else:
        await message.answer(ai_answer, parse_mode="HTML", reply_markup=get_main_keyboard(lang))


@dp.message(F.text)
async def handle_text_messages(message: types.Message):
    """Barcha matnli xabarlar: Eslatma kiritish yoki to'g'ridan-to'g'ri Gemini AI suhbat."""
    if not await is_authorized(message):
        return

    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    text = message.text.strip()
    ctx = get_user_ctx(user_id)

    # 1. Eslatma matnini kutayotgan bo'lsa
    if ctx.get("state") == "waiting_rem_text":
        ctx["rem_text"] = text
        ctx["state"] = "waiting_rem_time"
        await message.answer(tr("prompt_rem_time", lang), parse_mode="HTML", reply_markup=get_cancel_keyboard(lang))
        return

    # 2. Eslatma vaqtini kutayotgan bo'lsa
    if ctx.get("state") == "waiting_rem_time":
        target_dt = parse_reminder_time(text)
        if not target_dt:
            await message.answer(
                "⚠️ Vaqt formati tushunarsiz bo'ldi. Qaytadan kiriting:\n(Masalan: <code>15 daqiqa</code> yoki <code>18:30</code>)",
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard(lang)
            )
            return

        rem_text = ctx.get("rem_text") or "Eslatma"
        rem_at_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")
        add_reminder(user_id, rem_text, rem_at_str)

        ctx["state"] = None
        ctx["rem_text"] = None

        formatted_time = format_datetime(target_dt, lang)
        confirm_text = tr("rem_created", lang, text=rem_text, time=formatted_time)
        await message.answer(confirm_text, parse_mode="HTML", reply_markup=get_main_keyboard(lang))
        return

    # 3. Tabiiy tildagi avtomatik eslatma tekshiruvi (masalan: "10 daqiqadan keyin telefon qilish")
    time_match = parse_reminder_time(text)
    if time_match and any(k in text.lower() for k in ["daqiqa", "soat", "минут", "час", "ertaga", "эртага", "завтра", "indin"]):
        # Matn ichidan vaqt so'zini olib tashlab, qolganini eslatma mazmuni qilamiz
        clean_desc = re.sub(r'\b(\d+)\s*(?:daqiqa|daq|дақиқа|дакика|мин|минут|soat|st|соат|час|ertaga|эртага|завтра|indin)\w*\b', '', text, flags=re.IGNORECASE).strip()
        clean_desc = clean_desc.strip(" ,.-:;").strip()
        if not clean_desc or len(clean_desc) < 3:
            clean_desc = text

        rem_at_str = time_match.strftime("%Y-%m-%d %H:%M:%S")
        add_reminder(user_id, clean_desc, rem_at_str)
        formatted_time = format_datetime(time_match, lang)
        confirm_text = tr("rem_created", lang, text=clean_desc, time=formatted_time)
        await message.answer(f"⏰ <b>Aqlli Eslatma qabul qilindi!</b>\n\n{confirm_text}", parse_mode="HTML", reply_markup=get_main_keyboard(lang))
        return

    # 4. Doimiy Gemini AI Chat
    await bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)

    global http_session
    if not http_session or http_session.closed:
        http_session = aiohttp.ClientSession()

    loc_info = get_user_current_location(user_id)
    ai_response = await gemini_service.ask(
        user_id=user_id,
        prompt=text,
        session=http_session,
        location_info=loc_info
    )

    await message.answer(ai_response, parse_mode="HTML", reply_markup=get_main_keyboard(lang))


# ==========================================
# ASOSIY ISHGA TUSHIRISH (MAIN)
# ==========================================

async def main():
    """Botni to'liq ishga tushirish funksiyasi."""
    global http_session
    http_session = aiohttp.ClientSession()

    # Bot menyusiga buyruqlarni o'rnatish
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni qayta ishga tushirish"),
        BotCommand(command="qayerdaman", description="Hozirgi ko'changizni bilish (Radar)"),
        BotCommand(command="voice", description="Ovozli ogohlantirishni yoqish/o'chirish"),
        BotCommand(command="settings", description="Sozlamalar va til")
    ])

    # Fon rejimida eslatmalar tekshiruvchisini ishga tushirish
    asyncio.create_task(reminders_worker())

    logger.info("Hotira77 boti muvaffaqiyatli ishga tushdi (@Hotira77_bot). Xabarlar kutilmoqda...")

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
