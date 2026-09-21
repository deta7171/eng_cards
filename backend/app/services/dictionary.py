"""Free Dictionary API client (free, no key required).

https://dictionaryapi.dev/
"""

import httpx

DICTIONARY_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"


class DictionaryLookup:
    def __init__(self, transcription: str | None, part_of_speech: str | None, examples: list[str], audio_url: str | None):
        self.transcription = transcription
        self.part_of_speech = part_of_speech
        self.examples = examples
        self.audio_url = audio_url


async def lookup(word: str) -> DictionaryLookup | None:
    # Best-effort: transcription/examples are a nice-to-have, translation is the
    # part that must succeed. Never let this API being slow/down break word add.
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(DICTIONARY_URL.format(word=word))
            if response.status_code != 200:
                return None
            data = response.json()
    except httpx.HTTPError:
        return None

    if not data:
        return None
    entry = data[0]

    transcription = entry.get("phonetic")
    audio_url = None
    for phon in entry.get("phonetics", []):
        if not transcription and phon.get("text"):
            transcription = phon["text"]
        if not audio_url and phon.get("audio"):
            audio_url = phon["audio"]

    part_of_speech = None
    examples: list[str] = []
    for meaning in entry.get("meanings", []):
        if not part_of_speech:
            part_of_speech = meaning.get("partOfSpeech")
        for definition in meaning.get("definitions", []):
            example = definition.get("example")
            if example:
                examples.append(example)
            if len(examples) >= 3:
                break
        if len(examples) >= 3:
            break

    return DictionaryLookup(transcription, part_of_speech, examples, audio_url)
