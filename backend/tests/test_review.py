import uuid
from datetime import datetime, timedelta, timezone


def test_queue_without_auth_is_401(client):
    resp = client.get("/api/review/queue")
    assert resp.status_code == 401


def test_queue_includes_due_cards(auth_client):
    auth_client.post("/api/words", json={"text": "apple"})  # due_date defaults to now()

    resp = auth_client.get("/api/review/queue")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


def test_queue_excludes_future_due_cards(auth_client, db_session):
    add_resp = auth_client.post("/api/words", json={"text": "apple"})
    user_word_id = add_resp.json()["user_word_id"]

    from app.models import FSRSState

    state = db_session.get(FSRSState, uuid.UUID(user_word_id))
    state.due_date = datetime.now(timezone.utc) + timedelta(days=5)
    db_session.commit()

    resp = auth_client.get("/api/review/queue")
    assert resp.json()["items"] == []


def test_queue_orders_by_due_date_ascending(auth_client, db_session):
    from app.models import FSRSState

    ids_in_order = []
    for word_text, offset_minutes in [("apple", 10), ("banana", 1), ("cherry", 5)]:
        add_resp = auth_client.post("/api/words", json={"text": word_text})
        uw_id = add_resp.json()["user_word_id"]
        state = db_session.get(FSRSState, uuid.UUID(uw_id))
        state.due_date = datetime.now(timezone.utc) - timedelta(minutes=offset_minutes)
        ids_in_order.append((offset_minutes, uw_id))
    db_session.commit()

    resp = auth_client.get("/api/review/queue")
    returned_ids = [item["user_word_id"] for item in resp.json()["items"]]
    expected_order = [uw_id for _, uw_id in sorted(ids_in_order, key=lambda p: -p[0])]
    assert returned_ids == expected_order


def test_queue_respects_limit(auth_client):
    for i in range(5):
        auth_client.post("/api/words", json={"text": f"word{i}"})

    resp = auth_client.get("/api/review/queue?limit=2")
    assert len(resp.json()["items"]) == 2


def test_queue_only_shows_own_cards(auth_client, client, make_user):
    from tests.conftest import auth_headers

    auth_client.post("/api/words", json={"text": "apple"})

    other = make_user(email="other@example.com", google_id="google-5")
    resp = client.get("/api/review/queue", headers=auth_headers(other))
    assert resp.json()["items"] == []


def test_submit_review_updates_fsrs_state(auth_client):
    add_resp = auth_client.post("/api/words", json={"text": "apple"})
    user_word_id = add_resp.json()["user_word_id"]
    assert add_resp.json()["fsrs_state"]["state"] == "new"

    resp = auth_client.post(f"/api/review/{user_word_id}", json={"activity_type": "flip", "rating": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["fsrs_state"]["state"] in ("learning", "review")
    assert body["fsrs_state"]["reps"] == 1


def test_submit_review_invalid_rating_is_422(auth_client):
    add_resp = auth_client.post("/api/words", json={"text": "apple"})
    user_word_id = add_resp.json()["user_word_id"]

    resp = auth_client.post(f"/api/review/{user_word_id}", json={"activity_type": "flip", "rating": 0})
    assert resp.status_code == 422

    resp = auth_client.post(f"/api/review/{user_word_id}", json={"activity_type": "flip", "rating": 5})
    assert resp.status_code == 422


def test_submit_review_nonexistent_card_is_404(auth_client):
    resp = auth_client.post(f"/api/review/{uuid.uuid4()}", json={"activity_type": "flip", "rating": 3})
    assert resp.status_code == 404


def test_submit_review_for_another_users_card_is_404(auth_client, client, make_user):
    from tests.conftest import auth_headers

    add_resp = auth_client.post("/api/words", json={"text": "apple"})
    user_word_id = add_resp.json()["user_word_id"]

    other = make_user(email="other@example.com", google_id="google-6")

    resp = client.post(
        f"/api/review/{user_word_id}", json={"activity_type": "flip", "rating": 3}, headers=auth_headers(other)
    )
    assert resp.status_code == 404


def test_submit_review_creates_review_log(auth_client, db_session):
    add_resp = auth_client.post("/api/words", json={"text": "apple"})
    user_word_id = add_resp.json()["user_word_id"]

    auth_client.post(f"/api/review/{user_word_id}", json={"activity_type": "multiple_choice", "rating": 3})

    from app.models import ReviewLog

    logs = db_session.query(ReviewLog).all()
    assert len(logs) == 1
    assert logs[0].activity_type == "multiple_choice"
    assert logs[0].rating == 3


def test_repeated_again_ratings_eventually_increment_lapses(auth_client, db_session):
    """A card only counts as a "lapse" once it has graduated out of the
    initial learning phase and regresses on a later review - see
    app.services.fsrs_service.review's was_review_state check."""
    add_resp = auth_client.post("/api/words", json={"text": "apple"})
    user_word_id = add_resp.json()["user_word_id"]

    from app.models import FSRSState

    state = None
    for _ in range(6):
        auth_client.post(f"/api/review/{user_word_id}", json={"activity_type": "flip", "rating": 3})
        state = db_session.get(FSRSState, uuid.UUID(user_word_id))
        db_session.refresh(state)
        if state.state == "review":
            break

    assert state is not None
    assert state.state == "review"

    resp = auth_client.post(f"/api/review/{user_word_id}", json={"activity_type": "flip", "rating": 1})
    assert resp.json()["fsrs_state"]["lapses"] == 1
