"""Wraps py-fsrs (package name: fsrs) so the rest of the app only deals
with plain values, never the library's Card/State/Rating objects directly.
"""

from datetime import datetime, timezone

from fsrs import Card, Rating, Scheduler, State

from app.models import FSRSState

_scheduler = Scheduler()

_STATE_TO_STR = {
    State.Learning: "learning",
    State.Review: "review",
    State.Relearning: "relearning",
}
_STR_TO_STATE = {v: k for k, v in _STATE_TO_STR.items()}


def _card_from_state(fsrs_state: FSRSState) -> Card:
    if fsrs_state.state == "new":
        return Card()
    return Card(
        state=_STR_TO_STATE[fsrs_state.state],
        step=fsrs_state.step,
        stability=fsrs_state.stability,
        difficulty=fsrs_state.difficulty,
        due=fsrs_state.due_date,
        last_review=fsrs_state.last_review,
    )


def review(fsrs_state: FSRSState, rating: int) -> None:
    """Runs one FSRS review step and writes the result back onto fsrs_state in place."""
    was_review_state = fsrs_state.state == "review"

    card = _card_from_state(fsrs_state)
    updated_card, _log = _scheduler.review_card(card, Rating(rating), datetime.now(timezone.utc))

    fsrs_state.state = _STATE_TO_STR[updated_card.state]
    fsrs_state.step = updated_card.step
    fsrs_state.stability = updated_card.stability
    fsrs_state.difficulty = updated_card.difficulty
    fsrs_state.due_date = updated_card.due
    fsrs_state.last_review = updated_card.last_review
    fsrs_state.reps += 1
    if was_review_state and rating == Rating.Again:
        fsrs_state.lapses += 1
