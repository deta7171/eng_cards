"""MyMemory translation API client (free, no key required).

https://mymemory.translated.net/doc/spec.php
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger("app.translation")

MYMEMORY_URL = "https://api.mymemory.translated.net/get"


async def translate_en_to_ru(text: str) -> str:
    params = {"q": text, "langpair": "en|ru"}
    if settings.mymemory_email:
        params["de"] = settings.mymemory_email

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(MYMEMORY_URL, params=params)
        except httpx.HTTPError:
            logger.exception("MyMemory request failed for %r", text)
            raise
        if response.status_code != 200:
            logger.error("MyMemory HTTP %s for %r: %s", response.status_code, text, response.text[:500])
            response.raise_for_status()
        data = response.json()

    translated = data.get("responseData", {}).get("translatedText")
    if not translated:
        logger.error("MyMemory returned no translation for %r, full response: %s", text, data)
        raise ValueError(f"MyMemory returned no translation for {text!r}")
    return translated
