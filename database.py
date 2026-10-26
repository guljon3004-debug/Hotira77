import sqlite3
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# DATA_DIR berilsa (masalan Railway volume: /data) baza o'sha yerda saqlanadi
DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "vault.db")


def get_connection():
    """SQLite ma'lumotlar bazasiga ulanish yaratadi."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Barcha kerakli jadvallarni yaratadi."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Ish vaqti va davomat jadvali (Wi-Fi va qo'lda belgilash)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,         -- 'YYYY-MM-DD'
            check_in_time TEXT,             -- 'HH:MM:SS'
            check_out_time TEXT,            -- 'HH:MM:SS'
            duration_minutes INTEGER DEFAULT 0,
            status TEXT DEFAULT 'working',   -- 'working', 'completed'
            method TEXT DEFAULT 'wifi',     -- 'wifi' yoki 'manual'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Hujjatlar jadvali (Faqat rasmiy hujjatlar: PDF, DOCX, XLSX, TXT, ZIP)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            file_unique_id TEXT,
            file_name TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            file_ext TEXT,
            caption TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Shaxsiy media va qaydlar jadvali (Eski ma'lumotlar bilan moslik uchun)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            file_id TEXT,
            file_unique_id TEXT,
            file_name TEXT,
            file_size INTEGER DEFAULT 0,
            caption TEXT,
            category TEXT NOT NULL,
            is_favorite INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Eslatmalar va vazifalar jadvali
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            remind_at TEXT NOT NULL, -- ISO: YYYY-MM-DD HH:MM:SS
            is_completed INTEGER DEFAULT 0,
            repeat TEXT DEFAULT 'none', -- 'none', 'daily'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Maxsus papkalar / kategoriyalar jadvali
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '📁',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name)
        )
        """)

        # Sozlamalar va til jadvali
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            language TEXT DEFAULT 'uz',
            voice_enabled INTEGER DEFAULT 1
        )
        """)

        # voice_enabled ustuni mavjud bo'lmasa qo'shamiz
        try:
            cursor.execute("ALTER TABLE user_settings ADD COLUMN voice_enabled INTEGER DEFAULT 1")
        except Exception:
            pass

        # Ruxsat etilgan foydalanuvchilar (Oq ro'yxat / Whitelist)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS authorized_users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT DEFAULT 'staff',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Xavfsizlik hodisalari (Begona urinishlar logi)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT,
            username TEXT,
            message_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Indekslar
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_user_date ON work_attendance(user_id, work_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_user ON documents(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(is_completed, remind_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sec_user ON security_logs(user_id, created_at)")

        conn.commit()
    logger.info("Ma'lumotlar bazasi tayyor: %s", DB_PATH)


# ==========================================
# WORK ATTENDANCE (DAVOMAT VA ISH VAQTI)
# ==========================================

def record_check_in(user_id: int, method: str = "wifi") -> dict:
    """
    Ishga kelishni qayd etadi.
    Qaytaradi: {"status": "checked_in"|"already_active", "check_in_time": str, "work_date": str, "method": str}
    """
    now = datetime.now()
    work_date = now.strftime("%Y-%m-%d")
    check_in_time = now.strftime("%H:%M:%S")

    with get_connection() as conn:
        cursor = conn.cursor()
        # Bugungi faol (hali chiqib ketilmagan) sessiyani tekshiramiz
        cursor.execute("""
        SELECT * FROM work_attendance 
        WHERE user_id = ? AND work_date = ? AND status = 'working'
        ORDER BY id DESC LIMIT 1
        """, (user_id, work_date))
        active = cursor.fetchone()

        if active:
            return {
                "status": "already_active",
                "check_in_time": active["check_in_time"],
                "work_date": active["work_date"],
                "method": active["method"]
            }

        cursor.execute("""
        INSERT INTO work_attendance (user_id, work_date, check_in_time, status, method)
        VALUES (?, ?, ?, 'working', ?)
        """, (user_id, work_date, check_in_time, method))
        conn.commit()

        return {
            "status": "checked_in",
            "check_in_time": check_in_time,
            "work_date": work_date,
            "method": method
        }


def record_check_out(user_id: int, method: str = "wifi") -> dict:
    """
    Ishdan ketishni qayd etadi va ishlagan vaqtni hisoblaydi.
    Qaytaradi: {"status": "checked_out"|"no_active_session", "check_in_time": ..., "check_out_time": ..., "hours": int, "minutes": int}
    """
    now = datetime.now()
    check_out_time = now.strftime("%H:%M:%S")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM work_attendance 
        WHERE user_id = ? AND status = 'working'
        ORDER BY id DESC LIMIT 1
        """, (user_id,))
        active = cursor.fetchone()

        if not active:
            return {"status": "no_active_session"}

        session_id = active["id"]
        start_time_str = active["check_in_time"]
        start_date_str = active["work_date"]

        try:
            start_dt = datetime.strptime(f"{start_date_str} {start_time_str}", "%Y-%m-%d %H:%M:%S")
            diff = now - start_dt
            duration_minutes = max(1, int(diff.total_seconds() // 60))
        except Exception:
            duration_minutes = 0

        hours = duration_minutes // 60
        minutes = duration_minutes % 60

        cursor.execute("""
        UPDATE work_attendance 
        SET check_out_time = ?, duration_minutes = ?, status = 'completed'
        WHERE id = ?
        """, (check_out_time, duration_minutes, session_id))
        conn.commit()

        return {
            "status": "checked_out",
            "check_in_time": start_time_str,
            "check_out_time": check_out_time,
            "duration_minutes": duration_minutes,
            "hours": hours,
            "minutes": minutes,
            "work_date": start_date_str
        }


def get_today_attendance(user_id: int) -> dict | None:
    """Bugungi davomat holatini qaytaradi."""
    work_date = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM work_attendance 
        WHERE user_id = ? AND work_date = ?
        ORDER BY id DESC LIMIT 1
        """, (user_id, work_date))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_monthly_attendance(user_id: int, year: int = None, month: int = None) -> tuple[list, dict]:
    """
    Oylik davomat hisoboti va statistikasini beradi.
    Qaytaradi: (records_list, summary_dict)
    """
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    month_prefix = f"{year:04d}-{month:02d}-%"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM work_attendance 
        WHERE user_id = ? AND work_date LIKE ?
        ORDER BY work_date DESC, id DESC
        """, (user_id, month_prefix))
        rows = [dict(r) for r in cursor.fetchall()]

        total_days = len(set(r["work_date"] for r in rows))
        total_minutes = sum(r["duration_minutes"] or 0 for r in rows)
        total_hours = total_minutes // 60
        remaining_mins = total_minutes % 60

        avg_minutes_per_day = (total_minutes // total_days) if total_days > 0 else 0
        avg_hours = avg_minutes_per_day // 60
        avg_mins = avg_minutes_per_day % 60

        summary = {
            "year": year,
            "month": month,
            "total_days": total_days,
            "total_minutes": total_minutes,
            "total_hours": total_hours,
            "remaining_mins": remaining_mins,
            "avg_hours": avg_hours,
            "avg_mins": avg_mins,
        }
        return rows, summary


# ==========================================
# DOCUMENTS (HUJJATLAR ARXIVI)
# ==========================================

def add_document(user_id: int, file_id: str = "", file_unique_id: str = "",
                 file_name: str = "", file_size: int = 0, file_ext: str = "",
                 caption: str = "", file_type: str = "document", file_path: str = "") -> int:
    """Rasmiy hujjat yoki xotirani saqlaydi (ham documents, ham vault_items ga)."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO documents (user_id, file_id, file_unique_id, file_name, file_size, file_ext, caption)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, file_id, file_unique_id, file_name, file_size, file_ext or file_type, caption))
            conn.commit()
    except Exception:
        pass

    return add_vault_item(
        user_id=user_id,
        item_type=file_type or "document",
        file_id=file_id,
        file_unique_id=file_unique_id,
        file_name=file_name,
        file_size=file_size,
        caption=caption,
        category="documents" if file_type == "document" else (file_type + "s"),
        local_path=file_path
    )


def get_documents(user_id: int, search_query: str = None, page: int = 1, per_page: int = 25) -> list:
    """Barcha xotiralar va fayllar ro'yxatini to'g'ridan-to'g'ri list qilib beradi."""
    items, _ = get_vault_items(user_id=user_id, page=page, per_page=per_page, search_query=search_query)
    return items


def get_document(doc_id: int, user_id: int = None) -> dict | None:
    """Bitta hujjat yoki xotira ma'lumotini oladi."""
    item = get_vault_item(doc_id, user_id)
    if item:
        return item
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
        else:
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_document(doc_id: int, user_id: int = None) -> bool:
    """Hujjat yoki xotirani o'chiradi."""
    del_vault = delete_vault_item(doc_id, user_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("DELETE FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
        else:
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        return del_vault or (cursor.rowcount > 0)


# ==========================================
# VAULT (XAZINA) AMALLARI
# ==========================================

def add_vault_item(user_id: int, item_type: str, file_id: str = None,
                   file_unique_id: str = None, file_name: str = None,
                   file_size: int = 0, caption: str = "", category: str = None,
                   is_favorite: int = 0, local_path: str = None) -> int:
    """Yangi fayl yoki qayd saqlaydi va uning ID sini qaytaradi."""
    if not category:
        type_to_cat = {
            "photo": "photos",
            "video": "videos",
            "document": "documents",
            "audio": "audios",
            "voice": "audios",
            "note": "notes",
            "url": "bookmarks"
        }
        category = type_to_cat.get(item_type, "notes")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO vault_items (user_id, item_type, file_id, file_unique_id, file_name, file_size, caption, category, is_favorite, local_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, item_type, file_id, file_unique_id, file_name, file_size, caption, category, is_favorite, local_path))
        conn.commit()
        return cursor.lastrowid


def get_vault_item(item_id: int, user_id: int = None):
    """Bitta elementni ID bo'yicha oladi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM vault_items WHERE id = ? AND user_id = ?", (item_id, user_id))
        else:
            cursor.execute("SELECT * FROM vault_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_vault_item(item_id: int, user_id: int = None) -> bool:
    """Elementni o'chiradi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("DELETE FROM vault_items WHERE id = ? AND user_id = ?", (item_id, user_id))
        else:
            cursor.execute("DELETE FROM vault_items WHERE id = ?", (item_id,))
        conn.commit()
        return cursor.rowcount > 0


def toggle_vault_favorite(item_id: int, user_id: int) -> int:
    """Yulduzcha (Tanlanganlar) holatini almashtiradi (1 yoki 0) va yangi holatni qaytaradi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_favorite FROM vault_items WHERE id = ? AND user_id = ?", (item_id, user_id))
        row = cursor.fetchone()
        if not row:
            return 0
        new_val = 0 if row["is_favorite"] else 1
        cursor.execute("UPDATE vault_items SET is_favorite = ? WHERE id = ? AND user_id = ?", (new_val, item_id, user_id))
        conn.commit()
        return new_val


def update_vault_caption(item_id: int, user_id: int, new_caption: str) -> bool:
    """Element izohini/matnini yangilaydi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE vault_items SET caption = ? WHERE id = ? AND user_id = ?", (new_caption, item_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


def update_vault_local_path(item_id: int, local_path: str) -> bool:
    """Fayl lokal diskka yuklangandan so'ng uning manzilini bazada yangilaydi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE vault_items SET local_path = ? WHERE id = ?", (local_path, item_id))
        conn.commit()
        return cursor.rowcount > 0


def get_vault_stats(user_id: int) -> dict:
    """Foydalanuvchining shaxsiy xazinasi bo'yicha to'liq statistikani beradi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN category = 'photos' THEN 1 ELSE 0 END) as photos,
            SUM(CASE WHEN category = 'videos' THEN 1 ELSE 0 END) as videos,
            SUM(CASE WHEN category = 'documents' THEN 1 ELSE 0 END) as documents,
            SUM(CASE WHEN category = 'notes' THEN 1 ELSE 0 END) as notes,
            SUM(CASE WHEN category = 'audios' THEN 1 ELSE 0 END) as audios,
            SUM(CASE WHEN category = 'bookmarks' THEN 1 ELSE 0 END) as bookmarks,
            SUM(CASE WHEN is_favorite = 1 THEN 1 ELSE 0 END) as favorites
        FROM vault_items
        WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        return {
            "total": row["total"] or 0,
            "photos": row["photos"] or 0,
            "videos": row["videos"] or 0,
            "documents": row["documents"] or 0,
            "notes": row["notes"] or 0,
            "audios": row["audios"] or 0,
            "bookmarks": row["bookmarks"] or 0,
            "favorites": row["favorites"] or 0,
            "gallery": (row["photos"] or 0) + (row["videos"] or 0) + (row["audios"] or 0),
        }


def get_vault_items(user_id: int, category: str = None, is_favorite: bool = False,
                    page: int = 1, per_page: int = 5, search_query: str = None) -> tuple[list, int]:
    """
    Kategoriya yoki qidiruv bo'yicha elementlar ro'yxatini sahifalab beradi.
    Qaytaradi: (items_list, total_count)
    """
    conditions = ["user_id = ?"]
    params = [user_id]

    if is_favorite:
        conditions.append("is_favorite = 1")
    elif category == "gallery":
        conditions.append("category IN ('photos', 'videos', 'audios')")
    elif category:
        conditions.append("category = ?")
        params.append(category)

    if search_query:
        conditions.append("(caption LIKE ? OR file_name LIKE ?)")
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    where_sql = " AND ".join(conditions)

    with get_connection() as conn:
        cursor = conn.cursor()

        # Umumiy soni
        cursor.execute(f"SELECT COUNT(*) FROM vault_items WHERE {where_sql}", params)
        total_count = cursor.fetchone()[0]

        # Sahifa elementlari
        offset = (page - 1) * per_page
        query_sql = f"""
        SELECT * FROM vault_items 
        WHERE {where_sql} 
        ORDER BY id DESC 
        LIMIT ? OFFSET ?
        """
        cursor.execute(query_sql, params + [per_page, offset])
        rows = [dict(r) for r in cursor.fetchall()]

        return rows, total_count


# ==========================================
# REMINDERS (ESLATMALAR) AMALLARI
# ==========================================

def add_reminder(user_id: int, text: str, remind_at_str: str, repeat: str = "none") -> int:
    """Yangi eslatma qo'shadi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO reminders (user_id, text, remind_at, repeat)
        VALUES (?, ?, ?, ?)
        """, (user_id, text, remind_at_str, repeat))
        conn.commit()
        return cursor.lastrowid


def get_due_reminders():
    """Hozirgi vaqtda yuborilishi kerak bo'lgan eslatmalarni oladi."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM reminders 
        WHERE is_completed = 0 AND remind_at <= ?
        ORDER BY remind_at ASC
        """, (now_str,))
        return [dict(r) for r in cursor.fetchall()]


def mark_reminder_completed(reminder_id: int, repeat: str = "none"):
    """Eslatmani bajarildi deb belgilaydi (agar takroriy bo'lsa keyingi kunga o'tkazadi)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if repeat == "daily":
            # Ertangi kunga o'tkazish
            cursor.execute("SELECT remind_at FROM reminders WHERE id = ?", (reminder_id,))
            row = cursor.fetchone()
            if row:
                try:
                    dt = datetime.fromisoformat(row["remind_at"])
                    next_dt = dt + timedelta(days=1)
                    cursor.execute("UPDATE reminders SET remind_at = ? WHERE id = ?", (next_dt.strftime("%Y-%m-%d %H:%M:%S"), reminder_id))
                except Exception:
                    cursor.execute("UPDATE reminders SET is_completed = 1 WHERE id = ?", (reminder_id,))
            else:
                cursor.execute("UPDATE reminders SET is_completed = 1 WHERE id = ?", (reminder_id,))
        else:
            cursor.execute("UPDATE reminders SET is_completed = 1 WHERE id = ?", (reminder_id,))
        conn.commit()


def snooze_reminder(reminder_id: int, minutes: int = 10) -> bool:
    """Eslatmani bir necha daqiqaga kechiktiradi."""
    new_dt = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE reminders SET remind_at = ?, is_completed = 0 WHERE id = ?", (new_dt, reminder_id))
        conn.commit()
        return cursor.rowcount > 0


def get_user_reminders(user_id: int, show_completed: bool = False, limit: int = 20) -> list:
    """Foydalanuvchining eslatmalari ro'yxatini oladi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if show_completed:
            cursor.execute("""
            SELECT * FROM reminders 
            WHERE user_id = ? 
            ORDER BY is_completed ASC, remind_at ASC 
            LIMIT ?
            """, (user_id, limit))
        else:
            cursor.execute("""
            SELECT * FROM reminders 
            WHERE user_id = ? AND is_completed = 0
            ORDER BY remind_at ASC 
            LIMIT ?
            """, (user_id, limit))
        return [dict(r) for r in cursor.fetchall()]


def delete_reminder(reminder_id: int, user_id: int = None) -> bool:
    """Eslatmani butunlay o'chiradi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id))
        else:
            cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        conn.commit()
        return cursor.rowcount > 0


# ==========================================
# TIL VA SOZLAMALAR (SETTINGS)
# ==========================================

def get_user_lang(user_id: int) -> str:
    """Foydalanuvchi tanlagan tilni qaytaradi ('uz' yoki 'ru')."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM user_settings WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row["language"] if row and row["language"] else "uz"


def set_user_lang(user_id: int, lang: str):
    """Foydalanuvchi tilini bazaga saqlaydi ('uz' yoki 'ru')."""
    clean_lang = "ru" if lang == "ru" else "uz"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO user_settings (user_id, language) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET language = excluded.language
        """, (user_id, clean_lang))
        conn.commit()


def is_voice_enabled(user_id: int) -> bool:
    """Ovozli ogohlantirish yoqilganligini tekshiradi (sukut bo'yicha True)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT voice_enabled FROM user_settings WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row["voice_enabled"] is not None:
            return bool(row["voice_enabled"])
        return True


def set_voice_enabled(user_id: int, enabled: bool):
    """Ovozli ogohlantirish holatini saqlaydi (1: yoqilgan, 0: o'chirilgan)."""
    val = 1 if enabled else 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO user_settings (user_id, voice_enabled) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET voice_enabled = excluded.voice_enabled
        """, (user_id, val))
        conn.commit()


# ==========================================
# XAVFSIZLIK VA RUXSATLAR (SECURITY & WHITELIST)
# ==========================================

def is_user_authorized(user_id: int, admin_id: str | int | None = None) -> bool:
    """Foydalanuvchi tizimga kirish huquqiga egaligini tekshiradi."""
    if admin_id and str(user_id).strip() == str(admin_id).strip():
        return True

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM authorized_users WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None


def authorize_user(user_id: int, full_name: str = "", role: str = "staff") -> bool:
    """Yangi xodim yoki foydalanuvchiga ruxsat beradi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO authorized_users (user_id, full_name, role) VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET full_name = excluded.full_name, role = excluded.role
        """, (user_id, full_name, role))
        conn.commit()
        return True


def revoke_user(user_id: int) -> bool:
    """Foydalanuvchidan ruxsatni bekor qiladi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM authorized_users WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_authorized_users() -> list[dict]:
    """Ruxsat berilgan barcha foydalanuvchilar ro'yxati."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM authorized_users ORDER BY id DESC")
        return [dict(r) for r in cursor.fetchall()]


def log_security_incident(user_id: int, full_name: str = "", username: str = "", message_text: str = "", action_attempted: str = "", details: str = ""):
    """Begona foydalanuvchining kirish urinishini qayd etadi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        msg = message_text or details or action_attempted or "Kirish urinishi"
        cursor.execute("""
        INSERT INTO security_logs (user_id, full_name, username, message_text)
        VALUES (?, ?, ?, ?)
        """, (user_id, full_name or "", username or "", (msg or "")[:500]))
        conn.commit()


def get_security_incidents(limit: int = 10) -> list[dict]:
    """Oxirgi xavfsizlik hodisalari (begona urinishlar)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM security_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cursor.fetchall()]


def get_security_incident_count() -> int:
    """Jami qaytarilgan begona urinishlar soni."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM security_logs")
        row = cursor.fetchone()
        return row["cnt"] if row else 0


