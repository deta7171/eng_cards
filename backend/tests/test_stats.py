import uuid
from datetime import datetime, timedelta, timezone


def test_stats_summary_without_auth_is_401(client):
    resp = client.get("/api/stats/summary")
    assert resp.status_code == 401


def test_stats_summary_counts(auth_client, db_session):
    from app.models import FSRSState

    add1 = auth_client.post("/api/words", json={"text": "apple"}).json()
    auth_client.post("/api/words", json={"text": "banana"})

    # make "apple" due in the future so due_today only counts banana
    state = db_session.get(FSRSState, uuid.UUID(add1["user_word_id"]))
    state.due_date = datetime.now(timezone.utc) + timedelta(days=3)
    db_session.commit()

    resp = auth_client.get("/api/stats/summary")
    body = resp.json()
    assert body["total_words"] == 2
    assert body["due_today"] == 1


def test_stats_summary_mastered_threshold(auth_client, db_session):
    from app.models import FSRSState

    add_resp = auth_client.post("/api/words", json={"text": "apple"}).json()
    state = db_session.get(FSRSState, uuid.UUID(add_resp["user_word_id"]))
    state.stability = 30  # above MASTERY_STABILITY_THRESHOLD (21)
    db_session.commit()

    resp = auth_client.get("/api/stats/summary")
    assert resp.json()["mastered"] == 1


def test_stats_summary_not_mastered_below_threshold(auth_client, db_session):
    from app.models import FSRSState

    add_resp = auth_client.post("/api/words", json={"text": "apple"}).json()
    state = db_session.get(FSRSState, uuid.UUID(add_resp["user_word_id"]))
    state.stability = 5
    db_session.commit()

    resp = auth_client.get("/api/stats/summary")
    assert resp.json()["mastered"] == 0


def test_stats_summary_by_topic(auth_client, make_topic, make_word):
    food = make_topic(slug="food", name_ru="Еда")
    apple = make_word(text="apple", topic=food, source="seed")
    auth_client.post(f"/api/suggestions/{apple.id}/add")

    resp = auth_client.get("/api/stats/summary")
    by_topic = {t["slug"]: t["word_count"] for t in resp.json()["by_topic"]}
    assert by_topic["food"] == 1


def test_streak_zero_with_no_reviews(auth_client):
    resp = auth_client.get("/api/stats/summary")
    assert resp.json()["streak_days"] == 0


def test_streak_one_after_reviewing_today(auth_client):
    add_resp = auth_client.post("/api/words", json={"text": "apple"}).json()
    auth_client.post(f"/api/review/{add_resp['user_word_id']}", json={"activity_type": "flip", "rating": 3})

    resp = auth_client.get("/api/stats/summary")
    assert resp.json()["streak_days"] == 1


def test_streak_counts_consecutive_days(auth_client, db_session, make_user):
    from app.models import ReviewLog, UserWord

    add_resp = auth_client.post("/api/words", json={"text": "apple"}).json()
    user_word_id = uuid.UUID(add_resp["user_word_id"])

    today = datetime.now(timezone.utc)
    for days_ago in (0, 1, 2):
        db_session.add(
            ReviewLog(
                user_word_id=user_word_id,
                activity_type="flip",
                rating=3,
                reviewed_at=today - timedelta(days=days_ago),
            )
        )
    db_session.commit()

    resp = auth_client.get("/api/stats/summary")
    assert resp.json()["streak_days"] == 3


def test_streak_breaks_on_gap(auth_client, db_session):
    from app.models import ReviewLog

    add_resp = auth_client.post("/api/words", json={"text": "apple"}).json()
    user_word_id = uuid.UUID(add_resp["user_word_id"])

    today = datetime.now(timezone.utc)
    # reviewed today and 3 days ago, but not yesterday/2-days-ago -> streak is just today
    for days_ago in (0, 3):
        db_session.add(
            ReviewLog(
                user_word_id=user_word_id,
                activity_type="flip",
                rating=3,
                reviewed_at=today - timedelta(days=days_ago),
            )
        )
    db_session.commit()

    resp = auth_client.get("/api/stats/summary")
    assert resp.json()["streak_days"] == 1


def test_history_aggregates_reviews_by_day(auth_client, db_session):
    from app.models import ReviewLog

    add_resp = auth_client.post("/api/words", json={"text": "apple"}).json()
    user_word_id = uuid.UUID(add_resp["user_word_id"])

    today = datetime.now(timezone.utc)
    db_session.add(ReviewLog(user_word_id=user_word_id, activity_type="flip", rating=3, reviewed_at=today))
    db_session.add(ReviewLog(user_word_id=user_word_id, activity_type="flip", rating=1, reviewed_at=today))
    db_session.commit()

    resp = auth_client.get("/api/stats/history?days=7")
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["reviews"] == 2
    assert items[0]["correct"] == 1
