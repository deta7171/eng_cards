import uuid

import httpx
import pytest

from app.services import dictionary, translation


def test_add_word_without_auth_is_401(client):
    resp = client.post("/api/words", json={"text": "apple"})
    assert resp.status_code == 401


def test_add_new_word_creates_deck_entry(auth_client, db_session):
    resp = auth_client.post("/api/words", json={"text": "apple"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["word"]["text"] == "apple"
    assert body["word"]["translation"] == "перевод-apple"
    assert body["fsrs_state"]["state"] == "new"
    assert body["fsrs_state"]["reps"] == 0

    from app.models import UserWord, Word

    assert db_session.query(Word).filter(Word.text == "apple").count() == 1
    assert db_session.query(UserWord).count() == 1


def test_add_word_normalizes_case_and_whitespace(auth_client, db_session):
    resp = auth_client.post("/api/words", json={"text": "  Apple  "})
    assert resp.status_code == 201
    assert resp.json()["word"]["text"] == "apple"


def test_add_word_reuses_existing_dictionary_entry(auth_client, make_word, db_session):
    existing = make_word(text="apple", translation_="яблоко-seeded")

    resp = auth_client.post("/api/words", json={"text": "apple"})
    assert resp.status_code == 201
    # reused the seeded row rather than re-translating
    assert resp.json()["word"]["id"] == str(existing.id)
    assert resp.json()["word"]["translation"] == "яблоко-seeded"

    from app.models import Word

    assert db_session.query(Word).filter(Word.text == "apple").count() == 1


def test_add_word_already_in_deck_is_409(auth_client):
    auth_client.post("/api/words", json={"text": "apple"})
    resp = auth_client.post("/api/words", json={"text": "apple"})
    assert resp.status_code == 409


def test_two_users_can_each_add_the_same_word(auth_client, client, make_user, db_session):
    from tests.conftest import auth_headers

    auth_client.post("/api/words", json={"text": "apple"})

    other = make_user(email="other@example.com", google_id="google-2")
    resp = client.post("/api/words", json={"text": "apple"}, headers=auth_headers(other))
    assert resp.status_code == 201

    from app.models import UserWord, Word

    assert db_session.query(Word).filter(Word.text == "apple").count() == 1
    assert db_session.query(UserWord).count() == 2


def test_add_word_translation_http_error_is_502(auth_client, monkeypatch):
    async def failing_translate(text):
        raise httpx.HTTPStatusError("429", request=None, response=httpx.Response(429))

    monkeypatch.setattr(translation, "translate_en_to_ru", failing_translate)

    resp = auth_client.post("/api/words", json={"text": "banana"})
    assert resp.status_code == 502


def test_add_word_translation_empty_result_is_502(auth_client, monkeypatch):
    async def empty_translate(text):
        raise ValueError("no translation")

    monkeypatch.setattr(translation, "translate_en_to_ru", empty_translate)

    resp = auth_client.post("/api/words", json={"text": "banana"})
    assert resp.status_code == 502


def test_add_word_dictionary_lookup_failure_still_succeeds(auth_client):
    """Free Dictionary API being down must not block adding a word - only
    the translation is required (see app.services.dictionary.lookup)."""
    resp = auth_client.post("/api/words", json={"text": "apple"})
    assert resp.status_code == 201
    assert resp.json()["word"]["transcription"] is None
    assert resp.json()["word"]["examples"] == []


def test_get_user_words_only_returns_own_deck(auth_client, client, make_user, db_session):
    from tests.conftest import auth_headers

    auth_client.post("/api/words", json={"text": "apple"})

    other = make_user(email="other@example.com", google_id="google-3")
    client.post("/api/words", json={"text": "banana"}, headers=auth_headers(other))

    resp = auth_client.get("/api/user-words")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["word"]["text"] == "apple"


def test_delete_user_word_removes_only_the_deck_entry(auth_client, db_session):
    add_resp = auth_client.post("/api/words", json={"text": "apple"})
    user_word_id = add_resp.json()["user_word_id"]

    resp = auth_client.delete(f"/api/user-words/{user_word_id}")
    assert resp.status_code == 204

    from app.models import UserWord, Word

    assert db_session.query(UserWord).count() == 0
    assert db_session.query(Word).filter(Word.text == "apple").count() == 1


def test_delete_nonexistent_user_word_is_404(auth_client):
    resp = auth_client.delete(f"/api/user-words/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_cannot_delete_another_users_word(auth_client, client, make_user):
    from tests.conftest import auth_headers

    add_resp = auth_client.post("/api/words", json={"text": "apple"})
    user_word_id = add_resp.json()["user_word_id"]

    other = make_user(email="other@example.com", google_id="google-4")

    resp = client.delete(f"/api/user-words/{user_word_id}", headers=auth_headers(other))
    assert resp.status_code == 404

    # and it must still exist for the original owner
    still_there = auth_client.get("/api/user-words")
    assert still_there.json()["total"] == 1


def test_browse_words_filters_by_topic(client, make_topic, make_word):
    food = make_topic(slug="food", name_ru="Еда")
    travel = make_topic(slug="travel", name_en="Travel", name_ru="Путешествия")
    make_word(text="apple", topic=food)
    make_word(text="airport", topic=travel)

    resp = client.get("/api/words?topic=food")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["text"] == "apple"


def test_browse_words_filters_by_level(client, make_word):
    make_word(text="apple", cefr_level="A1")
    make_word(text="ephemeral", cefr_level="C2")

    resp = client.get("/api/words?level=A1")
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["text"] == "apple"


def test_browse_words_search(client, make_word):
    make_word(text="apple")
    make_word(text="banana")

    resp = client.get("/api/words?search=app")
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["text"] == "apple"


def test_browse_words_pagination(client, make_word):
    for i in range(25):
        make_word(text=f"word{i:02d}")

    page1 = client.get("/api/words?page=1").json()
    page2 = client.get("/api/words?page=2").json()
    assert page1["total"] == 25
    assert len(page1["items"]) == 20
    assert len(page2["items"]) == 5
