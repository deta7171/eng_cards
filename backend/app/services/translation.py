"""MyMemory translation API client (free, no key required).

https://mymemory.translated.net/doc/spec.php
"""

import httpx

from app.config import settings

MYMEMORY_URL = "https://api.mymemory.translated.net/get"


async def translate_en_to_ru(text: str) -> str:
    params = {"q": text, "langpair": "en|ru"}
    if settings.mymemory_email:
        params["de"] = settings.mymemory_email

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(MYMEMORY_URL, params=params)
        response.raise_for_status()
        data = response.json()

    translated = data.get("responseData", {}).get("translatedText")
    if not translated:
        raise ValueError(f"MyMemory returned no translation for {text!r}")
    return translated
