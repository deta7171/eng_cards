import httpx

from app.services import dictionary

# See the matching comment in test_translation_service.py - conftest's
# autouse mock replaces dictionary.lookup wholesale for every test.
_real_lookup = dictionary.lookup


class _FakeResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


class _FakeAsyncClient:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url):
        if self._exc:
            raise self._exc
        return self._response


def _patch_client(monkeypatch, response=None, exc=None):
    monkeypatch.setattr(dictionary.httpx, "AsyncClient", lambda **kwargs: _FakeAsyncClient(response=response, exc=exc))


FULL_ENTRY = [
    {
        "word": "apple",
        "phonetic": "/ˈæp.əl/",
        "phonetics": [
            {"text": "/ˈæp.əl/", "audio": "https://example.com/apple-us.mp3"},
            {"text": "", "audio": ""},
        ],
        "meanings": [
            {
                "partOfSpeech": "noun",
                "definitions": [
                    {"definition": "A fruit.", "example": "I ate an apple."},
                    {"definition": "Another sense.", "example": "The apple of my eye."},
                ],
            }
        ],
    }
]


async def test_lookup_parses_full_entry(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse(200, FULL_ENTRY))

    result = await _real_lookup("apple")
    assert result is not None
    assert result.transcription == "/ˈæp.əl/"
    assert result.part_of_speech == "noun"
    assert result.audio_url == "https://example.com/apple-us.mp3"
    assert result.examples == ["I ate an apple.", "The apple of my eye."]


async def test_lookup_caps_examples_at_three(monkeypatch):
    entry = [
        {
            "meanings": [
                {
                    "partOfSpeech": "noun",
                    "definitions": [{"definition": f"d{i}", "example": f"example {i}"} for i in range(6)],
                }
            ]
        }
    ]
    _patch_client(monkeypatch, response=_FakeResponse(200, entry))

    result = await _real_lookup("apple")
    assert len(result.examples) == 3


async def test_lookup_definitions_without_examples_are_skipped(monkeypatch):
    entry = [{"meanings": [{"partOfSpeech": "noun", "definitions": [{"definition": "no example here"}]}]}]
    _patch_client(monkeypatch, response=_FakeResponse(200, entry))

    result = await _real_lookup("apple")
    assert result.examples == []


async def test_lookup_404_returns_none(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse(404, {"title": "No Definitions Found"}))

    result = await _real_lookup("asdfghjkl")
    assert result is None


async def test_lookup_empty_list_returns_none(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse(200, []))

    result = await _real_lookup("apple")
    assert result is None


async def test_lookup_network_error_returns_none_not_raises(monkeypatch):
    """Dictionary lookup is best-effort - network failure must degrade
    gracefully (translation is still required and handled separately)."""
    _patch_client(monkeypatch, exc=httpx.ConnectTimeout("timed out"))

    result = await _real_lookup("apple")
    assert result is None


async def test_lookup_falls_back_to_phonetics_array_when_top_level_phonetic_missing(monkeypatch):
    entry = [
        {
            "meanings": [{"partOfSpeech": "noun", "definitions": [{"definition": "x"}]}],
            "phonetics": [{"text": "", "audio": ""}, {"text": "/fɔːl.bæk/", "audio": "https://example.com/a.mp3"}],
        }
    ]
    _patch_client(monkeypatch, response=_FakeResponse(200, entry))

    result = await _real_lookup("fallback")
    assert result.transcription == "/fɔːl.bæk/"
    assert result.audio_url == "https://example.com/a.mp3"


async def test_lookup_no_phonetics_array_still_works(monkeypatch):
    entry = [{"meanings": [{"partOfSpeech": "verb", "definitions": [{"definition": "x"}]}]}]
    _patch_client(monkeypatch, response=_FakeResponse(200, entry))

    result = await _real_lookup("run")
    assert result.transcription is None
    assert result.audio_url is None
    assert result.part_of_speech == "verb"
