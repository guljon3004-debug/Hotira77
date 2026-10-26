import logging
from datetime import datetime, timedelta, timezone

import aiohttp

logger = logging.getLogger(__name__)

# O'zbekiston vaqti (UTC+5, yozgi/qishki vaqtga o'tish yo'q)
UZ_TZ = timezone(timedelta(hours=5))

# Markaziy bank rasmiy kurslari (bepul, kalitsiz)
CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/{code}/"

# kod -> (emoji, o'zbekcha nom, ruscha nom, matndan taniydigan so'zlar)
CURRENCIES = {
    "USD": ("💵", "AQSh dollari", "Доллар США", ("dollar", "доллар", "доллор", "usd", "$", "dolar")),
    "EUR": ("💶", "Yevro", "Евро", ("yevro", "evro", "евро", "eur", "€")),
    "RUB": ("🇷🇺", "Rossiya rubli", "Российский рубль", ("rubl", "рубль", "рубл", "rub", "рубли")),
}

# "kurs so'rayapman" degan ma'noni bildiruvchi so'zlar
RATE_WORDS = ("kurs", "курс", "valyuta", "валюта", "qancha", "necha", "сколько", "narx", "нарх", "цена", "почем")


def detect_rate_request(text: str) -> list[str] | None:
    """
    Qisqa matn valyuta kursini so'rayotgan bo'lsa, kerakli valyuta kodlarini qaytaradi (aks holda None).
    Valyuta aytilmasa (masalan "valyuta kursi") hammasini qaytaradi.
    """
    t = (text or "").lower().strip()
    if not t or len(t) > 60:
        return None
    found = [code for code, (_, _, _, words) in CURRENCIES.items() if any(w in t for w in words)]
    has_rate_word = any(w in t for w in RATE_WORDS)
    if found and has_rate_word:
        return found
    if has_rate_word and any(w in t for w in ("kurs", "курс", "valyuta", "валюта")):
        return list(CURRENCIES)
    return None


def uz_now() -> datetime:
    return datetime.now(UZ_TZ)


def _num(value: str) -> float:
    return float(str(value).replace(" ", "").replace(",", "."))


def _fmt(value: float, signed: bool = False) -> str:
    """12100.0 -> '12 100,00'; signed=True bo'lsa +/- belgisi bilan."""
    text = f"{abs(value):,.2f}".replace(",", " ").replace(".", ",")
    if signed:
        return ("+" if value > 0 else "-" if value < 0 else "") + text
    return text


async def fetch_rate(session: aiohttp.ClientSession, code: str = "USD") -> dict | None:
    """Markaziy bankdan valyuta kursini oladi. Xatolik bo'lsa None."""
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with session.get(CBU_URL.format(code=code), timeout=timeout) as resp:
            if resp.status != 200:
                logger.warning("CBU kurs API javobi (%s): HTTP %s", code, resp.status)
                return None
            data = await resp.json(content_type=None)
        item = data[0]
        return {
            "code": code,
            "nominal": str(item.get("Nominal", "1")),
            "rate": _num(item["Rate"]),
            "diff": _num(item.get("Diff", 0)),
            "date": item.get("Date", ""),
        }
    except Exception as e:
        logger.warning("CBU kurs API xatolik (%s): %s", code, e)
        return None


async def fetch_usd_rate(session: aiohttp.ClientSession) -> dict | None:
    return await fetch_rate(session, "USD")


def format_rate(info: dict, lang: str = "uz") -> str:
    """Kursni chiroyli matn qilib qaytaradi."""
    code = info.get("code", "USD")
    emoji, name_uz, name_ru, _ = CURRENCIES.get(code, ("💱", code, code, ()))
    diff = info["diff"]
    arrow = "▲" if diff > 0 else "▼" if diff < 0 else "•"
    nominal = info.get("nominal", "1")
    if lang == "ru":
        return (
            f"{emoji} <b>{name_ru} — курс ЦБ Узбекистана</b>\n\n"
            f"{nominal} {code} = <b>{_fmt(info['rate'])}</b> сум\n"
            f"{arrow} Изменение: {_fmt(diff, signed=True)} сум\n"
            f"📅 Дата: {info['date']}"
        )
    return (
        f"{emoji} <b>{name_uz} kursi (O'zR Markaziy banki)</b>\n\n"
        f"{nominal} {code} = <b>{_fmt(info['rate'])}</b> so'm\n"
        f"{arrow} O'zgarish: {_fmt(diff, signed=True)} so'm\n"
        f"📅 Sana: {info['date']}"
    )


def format_usd_rate(info: dict, lang: str = "uz") -> str:
    return format_rate(info, lang)
