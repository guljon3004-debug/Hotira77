import logging
from datetime import datetime, timedelta, timezone

import aiohttp

logger = logging.getLogger(__name__)

# O'zbekiston vaqti (UTC+5, yozgi/qishki vaqtga o'tish yo'q)
UZ_TZ = timezone(timedelta(hours=5))

# Markaziy bank rasmiy kurslari (bepul, kalitsiz)
CBU_USD_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/USD/"


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


async def fetch_usd_rate(session: aiohttp.ClientSession) -> dict | None:
    """Markaziy bankdan USD kursini oladi. Xatolik bo'lsa None."""
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with session.get(CBU_USD_URL, timeout=timeout) as resp:
            if resp.status != 200:
                logger.warning("CBU kurs API javobi: HTTP %s", resp.status)
                return None
            data = await resp.json(content_type=None)
        item = data[0]
        return {
            "rate": _num(item["Rate"]),
            "diff": _num(item.get("Diff", 0)),
            "date": item.get("Date", ""),
        }
    except Exception as e:
        logger.warning("CBU kurs API xatolik: %s", e)
        return None


def format_usd_rate(info: dict, lang: str = "uz") -> str:
    """Kursni chiroyli matn qilib qaytaradi."""
    diff = info["diff"]
    arrow = "▲" if diff > 0 else "▼" if diff < 0 else "•"
    if lang == "ru":
        return (
            "💵 <b>Курс доллара США (ЦБ Узбекистана)</b>\n\n"
            f"1 USD = <b>{_fmt(info['rate'])}</b> сум\n"
            f"{arrow} Изменение: {_fmt(diff, signed=True)} сум\n"
            f"📅 Дата: {info['date']}"
        )
    return (
        "💵 <b>AQSh dollari kursi (O'zR Markaziy banki)</b>\n\n"
        f"1 USD = <b>{_fmt(info['rate'])}</b> so'm\n"
        f"{arrow} O'zgarish: {_fmt(diff, signed=True)} so'm\n"
        f"📅 Sana: {info['date']}"
    )
