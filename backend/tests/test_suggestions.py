import uuid


def test_suggestions_without_auth_is_401(client):
    resp = client.get("/api/suggestions")
    assert resp.status_code == 401


def test_suggestions_only_returns_seed_words(auth_client, make_word):
    make_word(text="seed-word", source="seed")
    make_word(text="user-added-word", source="user_added")

    resp = auth_client.get("/api/suggestions")
    assert resp.status_code == 200
    texts = [w["text"] for w in resp.json()["items"]]
    assert "seed-word" in texts
    assert "user-added-word" not in texts


def test_suggestions_excludes_words_already_in_deck(auth_client, make_word):
    already_added = make_word(text="apple", source="seed")
    not_added = make_word(text="banana", source="seed")

    auth_client.post(f"/api/suggestions/{already_added.id}/add")

    resp = auth_client.get("/api/suggestions")
    texts = [w["text"] for w in resp.json()["items"]]
    assert "apple" not in texts
    assert "banana" in texts


def test_suggestions_filters_by_topic_and_level(auth_client, make_topic, make_word):
    food = make_topic(slug="food", name_ru="Еда")
    make_word(text="apple", topic=food, cefr_level="A1", source="seed")
    make_word(text="ephemeral", cefr_level="C2", source="seed")

    resp = auth_client.get("/api/suggestions?topic=food&level=A1")
    texts = [w["text"] for w in resp.json()["items"]]
    assert texts == ["apple"]


def test_suggestions_respects_count(auth_client, make_word):
    for i in range(10):
        make_word(text=f"word{i}", source="seed")

    resp = auth_client.get("/api/suggestions?count=3")
    assert len(resp.json()["items"]) == 3


def test_add_suggestion_creates_deck_entry_with_suggested_source(auth_client, make_word, db_session):
    word = make_word(text="apple", source="seed")

    resp = auth_client.post(f"/api/suggestions/{word.id}/add")
    assert resp.status_code == 201
    assert resp.json()["word"]["text"] == "apple"

    from app.models import UserWord

    user_word = db_session.query(UserWord).first()
    assert user_word.source == "suggested"


def test_add_suggestion_nonexistent_word_is_404(auth_client):
    resp = auth_client.post(f"/api/suggestions/{uuid.uuid4()}/add")
    assert resp.status_code == 404


def test_add_suggestion_already_in_deck_is_409(auth_client, make_word):
    word = make_word(text="apple", source="seed")
    auth_client.post(f"/api/suggestions/{word.id}/add")

    resp = auth_client.post(f"/api/suggestions/{word.id}/add")
    assert resp.status_code == 409
