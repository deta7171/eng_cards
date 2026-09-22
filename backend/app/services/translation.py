"""English -> Russian translation with a fallback chain.

Primary: MyMemory (free, no key: https://mymemory.translated.net/doc/spec.php).
Its anonymous quota is shared across every app on Render's free-tier IP pool
and can get exhausted by unrelated projects (this happened in production -
see the 429 handling below).

Fallback: the unofficial Google Translate "gtx" endpoint used internally by
several open-source translate clients. Undocumented and unsupported by
Google, but on a different IP pool/provider than MyMemory, so it acts as
independent redundancy when MyMemory's shared quota is the problem.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger("app.translation")

MYMEMORY_URL = "https://api.mymemory.translated.net/get"
GOOGLE_GTX_URL = "https://translate.googleapis.com/translate_a/single"


async def _translate_via_mymemory(text: str) -> str:
    params = {"q": text, "langpair": "en|ru"}
    if settings.mymemory_email:
        params["de"] = settings.mymemory_email

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(MYMEMORY_URL, params=params)
        if response.status_code != 200:
            logger.error("MyMemory HTTP %s for %r: %s", response.status_code, text, response.text[:500])
            response.raise_for_status()
        data = response.json()

    translated = data.get("responseData", {}).get("translatedText")
    if not translated:
        raise ValueError(f"MyMemory returned no translation for {text!r}: {data}")
    return translated


async def _translate_via_google_gtx(text: str) -> str:
    params = {"client": "gtx", "sl": "en", "tl": "ru", "dt": "t", "q": text}

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(GOOGLE_GTX_URL, params=params)
        response.raise_for_status()
        data = response.json()

    # Response shape: [[["translated", "original", null, null, 3], ...], null, "en", ...]
    # - one inner list per sentence/chunk Google split the input into.
    try:
        translated = "".join(chunk[0] for chunk in data[0])
    except (IndexError, TypeError, KeyError) as exc:
        raise ValueError(f"Unexpected Google Translate response shape for {text!r}: {data}") from exc

    if not translated:
        raise ValueError(f"Google Translate returned no translation for {text!r}")
    return translated


async def translate_en_to_ru(text: str) -> str:
    try:
        return await _translate_via_mymemory(text)
    except (httpx.HTTPError, ValueError):
        logger.exception("MyMemory translation failed for %r, falling back to Google Translate", text)

    return await _translate_via_google_gtx(text)
