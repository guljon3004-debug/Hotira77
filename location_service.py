import math
import logging
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)

# Foydalanuvchilarning oxirgi joylashuvlari:
# user_id -> {"lat": float, "lon": float, "road": str, "district": str, "city": str, "display_name": str, "updated_at": datetime, "is_live": bool}
user_live_locations: dict[int, dict] = {}

# Kesh: (rounded_lat, rounded_lon) -> address_dict
address_cache: dict[tuple, dict] = {}


def calculate_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Ikki GPS nuqta orasidagi masofani (metrlarda) hisoblaydi (Haversine)."""
    R = 6371000  # Yer radiusi (metr)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


async def _nominatim(lat: float, lon: float, session: aiohttp.ClientSession) -> dict | None:
    """Nominatim (OpenStreetMap) orqali manzil. Xatolik bo'lsa None."""
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
    headers = {"User-Agent": "Hotira77Bot/1.0 (https://t.me/Hotira77_bot)"}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=6)) as resp:
            if resp.status != 200:
                logger.warning("Nominatim javobi: HTTP %s", resp.status)
                return None
            data = await resp.json(content_type=None)
    except Exception as e:
        logger.warning("Nominatim xatolik: %s", e)
        return None

    addr = data.get("address", {})
    display_name = data.get("display_name", "")
    road = (
        addr.get("road") or addr.get("pedestrian") or addr.get("footway") or addr.get("path") or
        addr.get("neighbourhood") or addr.get("residential") or addr.get("quarter") or
        addr.get("suburb") or addr.get("amenity") or addr.get("building") or ""
    )
    if not road and display_name:
        road = display_name.split(",")[0].strip()
    if not road:
        return None
    return {
        "road": road,
        "house": addr.get("house_number") or "",
        "district": addr.get("district") or addr.get("city_district") or addr.get("suburb") or addr.get("county") or "Toshkent",
        "city": addr.get("city") or addr.get("town") or addr.get("village") or addr.get("state") or "Toshkent",
        "display_name": display_name,
    }


async def _photon(lat: float, lon: float, session: aiohttp.ClientSession) -> dict | None:
    """Zaxira: Photon (OpenStreetMap asosida). Xatolik bo'lsa None."""
    url = f"https://photon.komoot.io/reverse?lat={lat}&lon={lon}&lang=en"
    try:
        async with session.get(url, headers={"User-Agent": "Hotira77Bot/1.0"}, timeout=aiohttp.ClientTimeout(total=6)) as resp:
            if resp.status != 200:
                logger.warning("Photon javobi: HTTP %s", resp.status)
                return None
            data = await resp.json(content_type=None)
    except Exception as e:
        logger.warning("Photon xatolik: %s", e)
        return None

    features = data.get("features") or []
    if not features:
        return None
    p = features[0].get("properties", {})
    road = p.get("street") or p.get("name") or p.get("locality") or p.get("district") or ""
    if not road:
        return None
    district = p.get("district") or p.get("county") or "Toshkent"
    city = p.get("city") or p.get("state") or "Toshkent"
    return {
        "road": road,
        "house": p.get("housenumber") or "",
        "district": district,
        "city": city,
        "display_name": ", ".join(x for x in (road, district, city) if x),
    }


async def resolve_address(lat: float, lon: float, session: aiohttp.ClientSession) -> dict | None:
    """
    GPS koordinatalarini ko'cha va tuman nomiga aylantiradi.
    Avval Nominatim, ishlamasa Photon sinab ko'riladi. Ikkalasi ham xato bersa None qaytaradi
    (soxta "Noma'lum ko'cha" yaratilmaydi, shunda yolg'on ogohlantirish chiqmaydi).
    """
    cache_key = (round(lat, 4), round(lon, 4))
    if cache_key in address_cache:
        return address_cache[cache_key]

    result = await _nominatim(lat, lon, session) or await _photon(lat, lon, session)
    if result:
        address_cache[cache_key] = result
        if len(address_cache) > 2000:
            address_cache.pop(next(iter(address_cache)))
    else:
        logger.error("Manzilni aniqlab bo'lmadi: %.5f, %.5f", lat, lon)
    return result


def update_user_location(user_id: int, lat: float, lon: float, address_info: dict, is_live: bool = False):
    """Foydalanuvchining so'nggi joylashuvini xotirada yangilaydi."""
    prev = user_live_locations.get(user_id, {})
    last_notified = address_info.get("last_notified_road") or prev.get("last_notified_road", "")
    last_time = address_info.get("last_notification_time") or prev.get("last_notification_time")

    user_live_locations[user_id] = {
        "lat": lat,
        "lon": lon,
        "road": address_info.get("road", ""),
        "house": address_info.get("house", ""),
        "district": address_info.get("district", ""),
        "city": address_info.get("city", ""),
        "display_name": address_info.get("display_name", ""),
        "updated_at": datetime.now(),
        "is_live": is_live,
        "last_notified_road": last_notified,
        "last_notification_time": last_time
    }


def get_user_current_location(user_id: int) -> dict | None:
    """Foydalanuvchining so'nggi joylashuvini qaytaradi."""
    return user_live_locations.get(user_id)


def format_location_text(loc_data: dict, lang: str = "uz") -> str:
    """Joylashuv ma'lumotini chiroyli minimalist matn qilib chiqaradi."""
    road = loc_data.get("road", "")
    house = loc_data.get("house", "")
    district = loc_data.get("district", "")
    city = loc_data.get("city", "")
    time_str = loc_data.get("updated_at", datetime.now()).strftime("%H:%M:%S")

    street_line = f"{road}, {house}".strip(", ") if road else "Aniqlanmagan ko'cha"
    area_line = f"{district}, {city}".strip(", ") if district else city

    if lang == "ru":
        return (
            "<b>ТЕКУЩЕЕ МЕСТОПОЛОЖЕНИЕ</b>\n\n"
            f"Улица: <code>{street_line}</code>\n"
            f"Район: {area_line}\n"
            f"Время обновления: {time_str}\n\n"
            "<i>Бот отслеживает ваши перемещения в реальном времени.</i>"
        )

    return (
        "<b>JORIY JOYLASHUVINGIZ</b>\n\n"
        f"Ko'cha: <code>{street_line}</code>\n"
        f"Hudud: {area_line}\n"
        f"Yangilangan vaqt: {time_str}\n\n"
        "<i>Tizim sizning harakatlanishingizni real vaqtda kuzatib bormoqda.</i>"
    )
