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
            raise httpx.HTTPStatusError("error", request=None, response=self)


class _FakeAsyncClient:
    def __init__(self, response=None, exc=None, **kwargs):
        self._response = response
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None):
        if self._exc:
            raise self._exc
        return self._response


def _patch_client(monkeypatch, response=None, exc=None):
    monkeypatch.setattr(
        translation.httpx, "AsyncClient", lambda **kwargs: _FakeAsyncClient(response=response, exc=exc)
    )


async def test_translate_success(monkeypatch):
    response = _FakeResponse(200, {"responseData": {"translatedText": "яблоко"}})
    _patch_client(monkeypatch, response=response)

    result = await _real_translate("apple")
    assert result == "яблоко"


async def test_translate_quota_exhausted_raises(monkeypatch):
    """Reproduces the exact production incident: MyMemory's shared free IP
    quota returns 200 with a warning payload, not a clean error status."""
    warning = {
        "responseData": {
            "translatedText": "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY."
        },
        "quotaFinished": None,
    }
    response = _FakeResponse(429, warning, text=str(warning))
    _patch_client(monkeypatch, response=response)

    with pytest.raises(httpx.HTTPStatusError):
        await _real_translate("banana")


async def test_translate_empty_response_data_raises_value_error(monkeypatch):
    response = _FakeResponse(200, {"responseData": {"translatedText": ""}})
    _patch_client(monkeypatch, response=response)

    with pytest.raises(ValueError):
        await _real_translate("xyzzy")


async def test_translate_missing_response_data_key_raises_value_error(monkeypatch):
    response = _FakeResponse(200, {})
    _patch_client(monkeypatch, response=response)

    with pytest.raises(ValueError):
        await _real_translate("xyzzy")


async def test_translate_network_error_propagates(monkeypatch):
    _patch_client(monkeypatch, exc=httpx.ConnectTimeout("timed out"))

    with pytest.raises(httpx.ConnectTimeout):
        await _real_translate("apple")


async def test_translate_passes_email_param_when_configured(monkeypatch):
    from app.config import settings

    captured = {}

    class RecordingClient(_FakeAsyncClient):
        async def get(self, url, params=None):
            captured.update(params or {})
            return _FakeResponse(200, {"responseData": {"translatedText": "ok"}})

    monkeypatch.setattr(translation.httpx, "AsyncClient", lambda **kwargs: RecordingClient())
    monkeypatch.setattr(settings, "mymemory_email", "someone@example.com")

    await _real_translate("apple")
    assert captured.get("de") == "someone@example.com"
