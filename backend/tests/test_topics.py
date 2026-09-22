def test_topics_no_auth_required(client):
    resp = client.get("/api/topics")
    assert resp.status_code == 200


def test_topics_returns_word_counts(client, make_topic, make_word):
    food = make_topic(slug="food", name_ru="Еда")
    travel = make_topic(slug="travel", name_en="Travel", name_ru="Путешествия")
    make_word(text="apple", topic=food)
    make_word(text="banana", topic=food)
    make_word(text="airport", topic=travel)

    resp = client.get("/api/topics")
    assert resp.status_code == 200
    by_slug = {t["slug"]: t["word_count"] for t in resp.json()}
    assert by_slug["food"] == 2
    assert by_slug["travel"] == 1


def test_topics_with_no_words_has_zero_count(client, make_topic):
    make_topic(slug="empty", name_en="Empty", name_ru="Пусто")

    resp = client.get("/api/topics")
    by_slug = {t["slug"]: t["word_count"] for t in resp.json()}
    assert by_slug["empty"] == 0
