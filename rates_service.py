import logging
import time
from datetime import datetime, timedelta, timezone

import aiohttp

logger = logging.getLogger(__name__)

# O'zbekiston vaqti (UTC+5, yozgi/qishki vaqtga o'tish yo'q)
UZ_TZ = timezone(timedelta(hours=5))

# Markaziy bank rasmiy kurslari (bepul, kalitsiz)
CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/{code}/"

# Zaxira manba: cbu.uz chet eldan (Railway serveri AQShda) ochilmasa ishlatiladi.
# Bu rasmiy emas, taxminiy bozor kursi.
FALLBACK_URL = "https://open.er-api.com/v6/latest/USD"

CBU_TIMEOUT = 6            # soniya
CBU_RETRY_AFTER = 600      # cbu.uz ochilmasa, 10 daqiqa urinib ko'rmaymiz
CACHE_TTL = 1800           # kursni 30 daqiqa eslab qolamiz
_cbu_down_until = 0.0
_cache: dict[str, tuple[float, dict]] = {}

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


async def _fetch_cbu(session: aiohttp.ClientSession, code: str) -> dict | None:
    global _cbu_down_until
    if time.monotonic() < _cbu_down_until:
        return None
    try:
        timeout = aiohttp.ClientTimeout(total=CBU_TIMEOUT)
        async with session.get(CBU_URL.format(code=code), timeout=timeout) as resp:
            if resp.status != 200:
                logger.warning("CBU kurs API javobi (%s): HTTP %s", code, resp.status)
                _cbu_down_until = time.monotonic() + CBU_RETRY_AFTER
                return None
            data = await resp.json(content_type=None)
        item = data[0]
        return {
            "code": code,
            "nominal": str(item.get("Nominal", "1")),
            "rate": _num(item["Rate"]),
            "diff": _num(item.get("Diff", 0)),
            "date": item.get("Date", ""),
            "approx": False,
        }
    except Exception as e:
        logger.warning("CBU kurs API xatolik (%s): %s %s", code, type(e).__name__, e)
        _cbu_down_until = time.monotonic() + CBU_RETRY_AFTER
        return None


async def _fetch_fallback(session: aiohttp.ClientSession, code: str) -> dict | None:
    """Zaxira: open.er-api.com (1 USD ga nisbatan kurslar) orqali so'mdagi kursni hisoblaydi."""
    try:
        async with session.get(FALLBACK_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                logger.warning("Zaxira kurs API javobi: HTTP %s", resp.status)
                return None
            data = await resp.json(content_type=None)
        rates = data["rates"]
        uzs_per_usd = float(rates["UZS"])
        per_usd = 1.0 if code == "USD" else float(rates[code])
        return {
            "code": code,
            "nominal": "1",
            "rate": uzs_per_usd / per_usd,
            "diff": None,
            "date": uz_now().strftime("%d.%m.%Y"),
            "approx": True,
        }
    except Exception as e:
        logger.warning("Zaxira kurs API xatolik (%s): %s %s", code, type(e).__name__, e)
        return None


async def fetch_rate(session: aiohttp.ClientSession, code: str = "USD") -> dict | None:
    """Avval Markaziy bankdan, ochilmasa zaxira manbadan kursni oladi. Ikkalasi ham xato bo'lsa None."""
    cached = _cache.get(code)
    if cached and time.monotonic() - cached[0] < CACHE_TTL:
        return cached[1]
    info = await _fetch_cbu(session, code) or await _fetch_fallback(session, code)
    if info:
        _cache[code] = (time.monotonic(), info)
    return info


async def fetch_usd_rate(session: aiohttp.ClientSession) -> dict | None:
    return await fetch_rate(session, "USD")


def format_rate(info: dict, lang: str = "uz") -> str:
    """Kursni chiroyli matn qilib qaytaradi."""
    code = info.get("code", "USD")
    emoji, name_uz, name_ru, _ = CURRENCIES.get(code, ("💱", code, code, ()))
    diff = info.get("diff")
    nominal = info.get("nominal", "1")
    approx = info.get("approx", False)
    if diff is None:
        diff_line = ""
    else:
        arrow = "▲" if diff > 0 else "▼" if diff < 0 else "•"
        diff_line = (f"{arrow} Изменение: {_fmt(diff, signed=True)} сум\n" if lang == "ru"
                     else f"{arrow} O'zgarish: {_fmt(diff, signed=True)} so'm\n")
    if lang == "ru":
        text = (
            f"{emoji} <b>{name_ru}</b>\n\n"
            f"{nominal} {code} = <b>{_fmt(info['rate'])}</b> сум\n"
            f"{diff_line}"
            f"📅 Дата: {info['date']}"
        )
        text += ("\n\nℹ️ <i>Сайт ЦБ сейчас недоступен — приблизительный рыночный курс.</i>" if approx
                 else "\n<i>Источник: ЦБ Узбекистана</i>")
    else:
        text = (
            f"{emoji} <b>{name_uz} kursi</b>\n\n"
            f"{nominal} {code} = <b>{_fmt(info['rate'])}</b> so'm\n"
            f"{diff_line}"
            f"📅 Sana: {info['date']}"
        )
        text += ("\n\nℹ️ <i>Markaziy bank sayti hozir ochilmadi — taxminiy bozor kursi.</i>" if approx
                 else "\n<i>Manba: O'zR Markaziy banki</i>")
    return text


def format_usd_rate(info: dict, lang: str = "uz") -> str:
    return format_rate(info, lang)
