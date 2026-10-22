import re
from datetime import datetime, timedelta

UZ_MONTHS = {
    1: "yanvar", 2: "fevral", 3: "mart", 4: "aprel", 5: "may", 6: "iyun",
    7: "iyul", 8: "avgust", 9: "sentabr", 10: "oktabr", 11: "noyabr", 12: "dekabr"
}

RU_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

def format_datetime(dt_obj: datetime, lang: str = "uz") -> str:
    """Sanani o'zbekcha yoki ruscha chiroyli formatda qaytaradi."""
    if lang == "ru":
        month_name = RU_MONTHS.get(dt_obj.month, "")
        return f"{dt_obj.day} {month_name}, {dt_obj.strftime('%H:%M')}"
    month_name = UZ_MONTHS.get(dt_obj.month, "")
    return f"{dt_obj.day}-{month_name}, {dt_obj.strftime('%H:%M')}"

# Orqaga moslik uchun
def format_datetime_uz(dt_obj: datetime) -> str:
    return format_datetime(dt_obj, "uz")


def parse_reminder_time(user_input: str) -> datetime | None:
    """
    Foydalanuvchi kiritgan vaqt matnini (o'zbek yoki rus tilida) tahlil qiladi.
    Formatlar:
    - '15:30' / '8:00'
    - 'ertaga 15:30' / 'завтра в 15:30' / 'завтра 9:00'
    - 'indin 14:00' / 'послезавтра в 14:00'
    - '15 daqiqa' / '15 минут' / '15m' / '15 min'
    - '2 soat' / '2 часа' / '1 час' / '2h'
    - '1 kun' / '1 день' / '2 дня'
    - '20.10 14:00' / '2026-10-20 14:00'
    """
    text = user_input.strip().lower()
    now = datetime.now()

    # 1. Nisbiy daqiqa: "15 daqiqa", "30 минут", "15m"
    minute_match = re.search(r"(\d+)\s*(?:daqiqa|daq|минут[уыа]?|мин|min|m)", text)
    if minute_match:
        mins = int(minute_match.group(1))
        return now + timedelta(minutes=mins)

    # 2. Nisbiy soat: "2 soat", "1 час", "3 часа", "2h"
    hour_match = re.search(r"(\d+)\s*(?:soat|st|час[аов]?|ч|h)", text)
    if hour_match:
        hours = int(hour_match.group(1))
        return now + timedelta(hours=hours)

    # 3. Nisbiy kun: "1 kun", "2 дня", "1 день"
    day_match = re.search(r"(\d+)\s*(?:kun|день|дня|дней|day|d)", text)
    if day_match:
        days = int(day_match.group(1))
        return now + timedelta(days=days)

    # 4. "ertaga 15:30", "завтра в 15:30", "zavtra 9:00"
    if any(k in text for k in ["ertaga", "zavtra", "завтра"]):
        time_match = re.search(r"(\d{1,2}):(\d{2})", text)
        if time_match:
            hh, mm = int(time_match.group(1)), int(time_match.group(2))
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

    # 5. "indin", "послезавтра"
    if any(k in text for k in ["indin", "послезавтра", "poslezavtra"]):
        time_match = re.search(r"(\d{1,2}):(\d{2})", text)
        if time_match:
            hh, mm = int(time_match.group(1)), int(time_match.group(2))
            after_tomorrow = now + timedelta(days=2)
            return after_tomorrow.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return (now + timedelta(days=2)).replace(hour=9, minute=0, second=0, microsecond=0)

    # 6. To'liq sana: YYYY-MM-DD HH:MM
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M")
    except ValueError:
        pass

    # 7. Sana: DD.MM.YYYY HH:MM
    try:
        return datetime.strptime(text, "%d.%m.%Y %H:%M")
    except ValueError:
        pass

    # 8. Sana: DD.MM HH:MM
    date_match = re.match(r"^(\d{1,2})[./](\d{1,2})\s+(\d{1,2}):(\d{2})$", text)
    if date_match:
        day, month, hh, mm = map(int, date_match.groups())
        year = now.year
        dt = datetime(year, month, day, hh, mm)
        if dt < now:
            dt = datetime(year + 1, month, day, hh, mm)
        return dt

    # 9. Faqat soat: "15:30" yoki "8:00"
    time_only_match = re.match(r"^(\d{1,2}):(\d{2})$", text)
    if time_only_match:
        hh, mm = int(time_only_match.group(1)), int(time_only_match.group(2))
        if 0 <= hh < 24 and 0 <= mm < 60:
            target_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if target_dt <= now:
                target_dt += timedelta(days=1)
            return target_dt

    return None
