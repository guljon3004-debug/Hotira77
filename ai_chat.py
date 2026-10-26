import os
import asyncio
import logging
import aiohttp
from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Siz aqlli, xushmuomala va do'stona AI assistantsiz (Google Gemini modeli asosida). "
    "Foydalanuvchilarga doimo tushunarli, aniq, foydali va samimiy javob bering. "
    "Foydalanuvchi qaysi tilda murojaat qilsa, o'sha tilda (asosan o'zbek tilida) ravon javob qaytaring. "
    "Kerakli o'rinlarda emojilardan foydalaning, ro'yxatlar va muhim fikrlarni chiroyli ajratib ko'rsating."
)


class GeminiChatService:
    """Google Gemini REST API orqali asinxron muloqot qiluvchi xizmat."""
    def get_system_prompt(self, location_info: dict | None = None) -> str:
        prompt = (
            "Siz aqlli, juda tezkor, xushmuomala va do'stona AI assistantsiz (Google Gemini modeli asosida). "
            "Foydalanuvchilarga doimo tushunarli, aniq, qisqa va foydali javob bering. "
            "O'zbek tilida ravon gapiring. "
        )
        if location_info:
            road = location_info.get("road") or "aniqlanmoqda"
            house = location_info.get("house") or ""
            district = location_info.get("district") or ""
            city = location_info.get("city") or "Toshkent"
            lat = location_info.get("lat", "")
            lon = location_info.get("lon", "")
            street_full = f"{road}, {house}".strip(", ")
            prompt += (
                f"\n[FOYDALANUVCHINING HOZIRGI JONLI JOYLASHUVI: Ko'cha: {street_full}, Tuman: {district}, "
                f"Shahar: {city}, GPS koordinatalar: {lat}, {lon}]. "
                "Foydalanuvchi qayerda ekanini yoki ko'chasini so'rasa yoki yaqin atrofdagi narsalarni so'rasa, "
                "aynishul joylashuvga asoslanib aniq, ishonchli va ravon ayting."
            )
        return prompt


    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = (api_key or GEMINI_API_KEY or "").strip()
        self.model = (model or GEMINI_MODEL or "gemini-flash-latest").strip()
        # Foydalanuvchilarning suhbat konteksti (tarixi): user_id -> list of contents
        self.user_histories: dict[int, list[dict]] = {}
        # Tarixda saqlanadigan maksimal xabarlar soni
        self.max_history_turns = 10
        self.fallback_models = ["gemini-flash-lite-latest", "gemini-2.5-flash", "gemini-flash-latest"]

    def is_configured(self) -> bool:
        """API kaliti sozlanganligini tekshiradi."""
        key = (self.api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        return bool(key and key != "SIZNING_GEMINI_API_KALITINGIZ")

    def get_api_key(self) -> str:
        """Har gal joriy API kalitini qaytaradi (muhitdan ham tekshiradi)."""
        current_key = (self.api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        return current_key

    def get_model(self) -> str:
        """Joriy model nomini qaytaradi."""
        return (self.model or os.getenv("GEMINI_MODEL", "gemini-flash-latest")).strip()

    async def _generate(self, session: aiohttp.ClientSession, payload: dict, total_timeout: int) -> tuple[int, dict]:
        """
        Gemini'ga so'rov yuboradi. Model band bo'lsa (429/500/503/504 yoki timeout)
        zaxira modellarga navbat bilan o'tadi. (status, javob) qaytaradi.
        """
        api_key = self.get_api_key()
        models = []
        for m in [self.get_model(), *self.fallback_models]:
            if m and m not in models:
                models.append(m)

        status, data = 0, {}
        for i, model in enumerate(models):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                timeout = aiohttp.ClientTimeout(total=total_timeout)
                async with session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout) as resp:
                    status = resp.status
                    data = await resp.json(content_type=None)
            except asyncio.TimeoutError:
                status, data = 504, {"error": {"message": "Timeout"}}
            except aiohttp.ClientConnectorError:
                raise

            if status not in (429, 500, 503, 504) and not (status == 404 and i > 0):
                return status, data
            logger.warning(f"Gemini [{model}] band ({status}), keyingi modelga o'tilmoqda...")
            await asyncio.sleep(1)
        return status, data

    def clear_history(self, user_id: int):
        """Foydalanuvchi suhbat tarixini tozalash."""
        if user_id in self.user_histories:
            self.user_histories.pop(user_id, None)

    async def ask(self, user_id: int, prompt: str, session: aiohttp.ClientSession, location_info: dict | None = None) -> str:
        """
        Foydalanuvchi savoliga Gemini AI orqali javob oladi.
        Kontekst (suhbat tarixi) avtomatik ravishda saqlanadi.
        """
        api_key = self.get_api_key()

        # Agar API kalit kiritilmagan bo'lsa
        if not self.is_configured():
            return (
                "⚠️ <b>Gemini API kaliti topilmadi!</b>\n\n"
                "AI Chat xizmatidan foydalanish uchun bot papkasidagi <b><code>.env</code></b> faylini oching va "
                "<b><code>GEMINI_API_KEY=...</code></b> qatoriga o'z API kalitingizni kiriting.\n\n"
                "🔑 <i>API kalitni bepul olish uchun:</i>\n"
                "<a href=\"https://aistudio.google.com/app/apikey\">https://aistudio.google.com/app/apikey</a> saytiga kiring."
            )


        # Foydalanuvchi tarixini olamiz yoki yangi boshlaymiz
        history = self.user_histories.get(user_id, [])

        # Yangi savolni qo'shamiz
        new_contents = list(history)
        new_contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": new_contents,
            "systemInstruction": {"parts": [{"text": self.get_system_prompt(location_info)}]},
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            }
        }

        try:
            status, data = await self._generate(session, payload, 45)

            if status == 200:
                candidates = data.get("candidates", [])
                if candidates:
                    candidate = candidates[0]
                    content = candidate.get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        reply_text = "".join(p.get("text", "") for p in parts).strip()

                        # Javobni tarixga qo'shamiz
                        new_contents.append({
                            "role": "model",
                            "parts": [{"text": reply_text}]
                        })

                        # Tarixni maksimal o'lchamda ushlab turamiz
                        if len(new_contents) > self.max_history_turns:
                            new_contents = new_contents[-self.max_history_turns:]

                        self.user_histories[user_id] = new_contents
                        return reply_text

                return "🤔 AI dan bo'sh javob qaytdi. Iltimos, boshqacha savol berib ko'ring."

            # Agar xatolik bo'lsa
            error_info = data.get("error", {})
            error_msg = error_info.get("message", "Noma'lum xatolik")
            status_code = status

            logger.error(f"Gemini API Error [{status_code}]: {error_msg}")

            if status_code == 400:
                if "API key not valid" in error_msg or "INVALID_ARGUMENT" in str(error_info):
                    return (
                        "❌ <b>Gemini API kaliti yaroqsiz!</b>\n\n"
                        "Iltimos, <code>.env</code> faylidagi <code>GEMINI_API_KEY</code> to'g'ri kiritilganini tekshiring."
                    )
                return f"❌ <b>So'rovda xatolik:</b>\n{error_msg}"
            elif status_code in (500, 503, 504):
                return "⏳ <b>Gemini AI hozir juda band.</b>\n\nGoogle serverlariga yuklama oshgan. Iltimos, 1-2 daqiqadan keyin qayta urinib ko'ring."
            elif status_code == 429:
                return (
                    "⏳ <b>So'rovlar limiti oshdi!</b>\n\n"
                    "Gemini API bepul tarifi bo'yicha limitga yetildi. Iltimos, birozdan keyin qayta urinib ko'ring."
                )
            else:
                return f"⚠️ <b>Gemini xizmatida xatolik ({status_code}):</b>\n{error_msg}"

        except aiohttp.ClientConnectorError:
            return "📡 <b>Internet yoki tarmoqqa ulanishda muammo bo'ldi.</b> Iltimos, internetingizni tekshiring."
        except asyncio.TimeoutError:
            return "⏱ <b>Gemini AI javob berish vaqti tugadi (Timeout).</b> Iltimos, qayta urinib ko'ring."
        except Exception as e:
            logger.exception("Gemini so'rovida kutilmagan xatolik:")
            return f"⚠️ <b>Kutilmagan xatolik yuz berdi:</b> {str(e)}"

    async def ask_audio(self, user_id: int, audio_bytes: bytes, mime_type: str, session: aiohttp.ClientSession, location_info: dict | None = None) -> str:
        """
        Foydalanuvchi yuborgan ovozli/audio xabarni Gemini AI ga yuboradi va javob matnini oladi.
        """
        import base64

        if not self.is_configured():
            return (
                "⚠️ <b>Gemini API kaliti topilmadi!</b>\n\n"
                "Ovozli AI xizmatidan foydalanish uchun <code>.env</code> fayliga "
                "<code>GEMINI_API_KEY</code> ni kiriting."
            )


        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        history = self.user_histories.get(user_id, [])

        # Yangi audio so'rov
        user_content = {
            "role": "user",
            "parts": [
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": audio_b64
                    }
                },
                {
                    "text": (
                        "Foydalanuvchi ushbu ovozli xabarni yubordi. "
                        "Uning nutqini tinglab, savoliga mos ravishda, o'zbek tilida samimiy, aniq va "
                        "ovoz bilan o'qishga qulay qilib (juda cho'zmasdan) javob bering."
                    )
                }
            ]
        }

        new_contents = list(history)
        new_contents.append(user_content)

        payload = {
            "contents": new_contents,
            "systemInstruction": {"parts": [{"text": self.get_system_prompt(location_info)}]},
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 256,
            }
        }

        try:
            status, data = await self._generate(session, payload, 60)

            if status == 200:
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        reply_text = "".join(p.get("text", "") for p in parts).strip()

                        # Javobni tarixga qo'shamiz
                        new_contents.append({
                            "role": "model",
                            "parts": [{"text": reply_text}]
                        })

                        if len(new_contents) > self.max_history_turns:
                            new_contents = new_contents[-self.max_history_turns:]

                        self.user_histories[user_id] = new_contents
                        return reply_text

                return "Audio xabaringiz eshitildi, ammo javob hosil qilib bo'lmadi. Iltimos, qayta yuboring."

            error_info = data.get("error", {})
            error_msg = error_info.get("message", "Noma'lum xatolik")
            logger.error(f"Gemini Audio Error [{status}]: {error_msg}")
            if status in (500, 503, 504):
                return "⏳ <b>Gemini AI hozir juda band.</b>\n\nGoogle serverlariga yuklama oshgan. Iltimos, 1-2 daqiqadan keyin qayta urinib ko'ring."
            return f"⚠️ <b>Ovozni tahlil qilishda xatolik ({status}):</b> {error_msg}"

        except Exception as e:
            logger.exception("Gemini audio so'rovida xatolik:")
            return f"⚠️ <b>Xatolik yuz berdi:</b> {str(e)}"


    async def ask_image(
        self,
        user_id: int,
        image_bytes: bytes,
        mime_type: str,
        caption: str,
        session: aiohttp.ClientSession
    ) -> str:
        """
        Foydalanuvchi yuborgan rasm va savolni Gemini AI ga yuboradi va tahlilini oladi.
        """
        import base64

        if not self.is_configured():
            return (
                "⚠️ <b>Gemini API kaliti topilmadi!</b>\n\n"
                "AI xizmatidan foydalanish uchun <code>.env</code> fayliga "
                "<code>GEMINI_API_KEY</code> ni kiriting."
            )


        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        history = self.user_histories.get(user_id, [])

        prompt_text = caption.strip() if caption and caption.strip() else (
            "Ushbu rasmni diqqat bilan ko'rib chiqing. Unda nimalar aks etgan, matnlar, hujjatlar yoki "
            "muhim tafsilotlar bo'lsa, o'zbek tilida chiroyli va tushunarli qilib tahlil qilib bering."
        )

        user_content = {
            "role": "user",
            "parts": [
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": img_b64
                    }
                },
                {"text": prompt_text}
            ]
        }

        new_contents = list(history)
        new_contents.append(user_content)

        payload = {
            "contents": new_contents,
            "systemInstruction": {"parts": [{"text": self.get_system_prompt(location_info)}]},
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            }
        }

        try:
            status, data = await self._generate(session, payload, 60)

            if status == 200:
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        reply_text = "".join(p.get("text", "") for p in parts).strip()

                        new_contents.append({
                            "role": "model",
                            "parts": [{"text": reply_text}]
                        })

                        if len(new_contents) > self.max_history_turns:
                            new_contents = new_contents[-self.max_history_turns:]

                        self.user_histories[user_id] = new_contents
                        return reply_text

                return "Rasm qabul qilindi, ammo javob hosil qilib bo'lmadi."

            error_info = data.get("error", {})
            error_msg = error_info.get("message", "Noma'lum xatolik")
            logger.error(f"Gemini Image Error [{status}]: {error_msg}")
            if status in (500, 503, 504):
                return "⏳ <b>Gemini AI hozir juda band.</b>\n\nGoogle serverlariga yuklama oshgan. Iltimos, 1-2 daqiqadan keyin qayta urinib ko'ring."
            return f"⚠️ <b>Rasmni tahlil qilishda xatolik ({status}):</b> {error_msg}"

        except Exception as e:
            logger.exception("Gemini rasm so'rovida xatolik:")
            return f"⚠️ <b>Xatolik yuz berdi:</b> {str(e)}"


# Global Gemini chat servisi
gemini_service = GeminiChatService()
