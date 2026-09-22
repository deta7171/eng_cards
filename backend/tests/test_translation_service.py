import httpx
import pytest

from app.services import translation

# The autouse `_mock_external_services` fixture in conftest.py replaces
# translation.translate_en_to_ru wholesale for every test, so these
# HTTP-level tests must call the real function captured here at import time
# (before any per-test monkeypatching happens) rather than going through the
# (patchable) module attribute.
_real_translate = translation.translate_en_to_ru


class _FakeResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or (str(json_data) if json_data else "")

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(f"HTTP {self.status_code}", request=None, response=self)


class _RoutingAsyncClient:
    """Routes based on which URL is requested, so mymemory and the Google
    fallback can be scripted independently in the same test."""

    def __init__(self, mymemory=None, google=None):
        self._mymemory = mymemory
        self._google = google

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None):
        outcome = self._mymemory if url == translation.MYMEMORY_URL else self._google
        if outcome is None:
            raise AssertionError(f"unexpected call to {url}")
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _patch(monkeypatch, mymemory=None, google=None):
    monkeypatch.setattr(translation.httpx, "AsyncClient", lambda **kwargs: _RoutingAsyncClient(mymemory, google))


def _mymemory_ok(text="перевод"):
    return _FakeResponse(200, {"responseData": {"translatedText": text}})


def _mymemory_quota_exhausted():
    warning = {"responseData": {"translatedText": "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY."}}
    return _FakeResponse(429, warning, text=str(warning))


def _google_ok(text="перевод"):
    # real shape: [[["translated", "original", null, null, 3], ...], null, "en"]
    return _FakeResponse(200, [[[text, "original", None, None, 3]], None, "en"])


async def test_translate_success_via_mymemory_does_not_call_google(monkeypatch):
    _patch(monkeypatch, mymemory=_mymemory_ok("яблоко"), google=AssertionError("google should not be called"))

    result = await _real_translate("apple")
    assert result == "яблоко"


async def test_translate_falls_back_to_google_when_mymemory_quota_exhausted(monkeypatch):
    """The actual production incident: MyMemory's shared free IP quota
    returns 429 with a warning payload; Google fallback should rescue it."""
    _patch(monkeypatch, mymemory=_mymemory_quota_exhausted(), google=_google_ok("банан"))

    result = await _real_translate("banana")
    assert result == "банан"


async def test_translate_falls_back_to_google_on_mymemory_empty_result(monkeypatch):
    _patch(monkeypatch, mymemory=_mymemory_ok(""), google=_google_ok("х"))

    result = await _real_translate("x")
    assert result == "х"


async def test_translate_falls_back_to_google_on_mymemory_network_error(monkeypatch):
    _patch(monkeypatch, mymemory=httpx.ConnectTimeout("timed out"), google=_google_ok("яблоко"))

    result = await _real_translate("apple")
    assert result == "яблоко"


async def test_translate_raises_when_both_providers_fail(monkeypatch):
    _patch(monkeypatch, mymemory=_mymemory_quota_exhausted(), google=_FakeResponse(500, None, text="server error"))

    with pytest.raises(httpx.HTTPStatusError):
        await _real_translate("banana")


async def test_translate_google_fallback_joins_multi_sentence_response(monkeypatch):
    google_response = _FakeResponse(200, [[["Привет ", None, None, None, 3], ["мир.", None, None, None, 3]], None, "en"])
    _patch(monkeypatch, mymemory=_mymemory_quota_exhausted(), google=google_response)

    result = await _real_translate("Hello world.")
    assert result == "Привет мир."


async def test_translate_google_fallback_empty_translation_raises_value_error(monkeypatch):
    _patch(monkeypatch, mymemory=_mymemory_quota_exhausted(), google=_google_ok(""))

    with pytest.raises(ValueError):
        await _real_translate("banana")


async def test_translate_google_fallback_unexpected_shape_raises_value_error(monkeypatch):
    _patch(monkeypatch, mymemory=_mymemory_quota_exhausted(), google=_FakeResponse(200, {"unexpected": "shape"}))

    with pytest.raises(ValueError):
        await _real_translate("banana")


async def test_translate_passes_email_param_when_configured(monkeypatch):
    from app.config import settings

    captured = {}

    class RecordingClient(_RoutingAsyncClient):
        async def get(self, url, params=None):
            if url == translation.MYMEMORY_URL:
                captured.update(params or {})
                return _mymemory_ok("ok")
            raise AssertionError("google should not be called")

    monkeypatch.setattr(translation.httpx, "AsyncClient", lambda **kwargs: RecordingClient())
    monkeypatch.setattr(settings, "mymemory_email", "someone@example.com")

    await _real_translate("apple")
    assert captured.get("de") == "someone@example.com"
