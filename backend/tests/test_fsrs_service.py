import uuid
from datetime import datetime, timezone

from app.models import FSRSState
from app.services import fsrs_service


def _new_state():
    return FSRSState(
        user_word_id=uuid.uuid4(),
        state="new",
        step=None,
        stability=None,
        difficulty=None,
        due_date=datetime.now(timezone.utc),
        reps=0,
        lapses=0,
        last_review=None,
    )


def test_review_moves_new_card_out_of_new_state():
    state = _new_state()
    fsrs_service.review(state, rating=3)

    assert state.state in ("learning", "review")
    assert state.reps == 1
    assert state.stability is not None
    assert state.difficulty is not None
    assert state.last_review is not None


def test_review_schedules_due_date_in_the_future():
    state = _new_state()
    fsrs_service.review(state, rating=3)
    assert state.due_date > datetime.now(timezone.utc)


def test_review_does_not_increment_lapses_from_new_state_even_on_again():
    state = _new_state()
    fsrs_service.review(state, rating=1)  # Again
    assert state.lapses == 0


def test_review_increments_lapses_only_when_regressing_from_review_state():
    state = _new_state()
    # graduate to "review" state with repeated Good ratings
    for _ in range(10):
        fsrs_service.review(state, rating=3)
        if state.state == "review":
            break
    assert state.state == "review"

    lapses_before = state.lapses
    fsrs_service.review(state, rating=1)  # Again, while already in "review"
    assert state.lapses == lapses_before + 1


def test_review_reps_increments_every_call():
    state = _new_state()
    for expected in range(1, 5):
        fsrs_service.review(state, rating=3)
        assert state.reps == expected
